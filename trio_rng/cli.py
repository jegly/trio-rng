#!/usr/bin/env python3
"""
trio-rng: Triple-Cascade Quantum Random Number Generator
Uses OpenSSL -> Qiskit -> Cirq cascade for random number generation
"""

import os
import sys
import random
import argparse
import hashlib
from typing import List, Optional

try:
    from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
    from qiskit_aer import Aer
except ImportError:
    print(
        "Error: qiskit and qiskit-aer are required. "
        "Install with: pip install qiskit qiskit-aer",
        file=sys.stderr,
    )
    sys.exit(1)

try:
    import cirq
except ImportError:
    print("Error: cirq is required. Install with: pip install cirq", file=sys.stderr)
    sys.exit(1)


class TrioRNG:
    """Triple-cascade random number generator using OpenSSL, Qiskit, and Cirq"""

    def __init__(self, bits: int, verbose: bool = False, seed: Optional[int] = None):
        if bits < 1:
            raise ValueError(f"bits must be >= 1, got {bits}")
        self.bits = bits
        self.verbose = verbose
        self.seed = seed

    def log(self, message: str) -> None:
        """Print verbose output if enabled"""
        if self.verbose:
            print(f"[VERBOSE] {message}")

    def openssl_stage(self) -> str:
        """Stage 1: Generate random bits using OpenSSL (os.urandom)"""
        self.log("Stage 1: OpenSSL random generation")

        num_bytes = (self.bits + 7) // 8

        if self.seed is not None:
            self.log(f"Using seed: {self.seed}")
            # FIX: chain each hash block from the previous block's digest,
            # not always from the same initial digest. The original code called
            # sha256(random_bytes) every iteration with the same `random_bytes`,
            # producing identical repeated 32-byte blocks.
            h = hashlib.sha256(str(self.seed).encode())
            random_bytes = h.digest()
            while len(random_bytes) < num_bytes:
                random_bytes += hashlib.sha256(random_bytes).digest()
                # advance the seed material so the next block differs
            random_bytes = random_bytes[:num_bytes]
        else:
            random_bytes = os.urandom(num_bytes)

        bitstring = "".join(format(byte, "08b") for byte in random_bytes)
        bitstring = bitstring[: self.bits]

        self.log(f"OpenSSL output ({len(bitstring)} bits): {bitstring}")
        self.log(f"OpenSSL hex: {hex(int(bitstring, 2))}")

        return bitstring

    def qiskit_stage(self, input_bits: str) -> str:
        """Stage 2: Process through Qiskit quantum circuit"""
        self.log("Stage 2: Qiskit quantum circuit")

        seed_value = int(input_bits, 2) if input_bits else 0
        num_qubits = max(1, min(self.bits, (seed_value % 10) + 1))

        self.log(f"Creating Qiskit circuit with {num_qubits} qubits")

        qr = QuantumRegister(num_qubits, "q")
        cr = ClassicalRegister(num_qubits, "c")
        qc = QuantumCircuit(qr, cr)

        # Apply Hadamard gates to create superposition
        for i in range(num_qubits):
            qc.h(qr[i])

        # Use input bits to add phase shifts for entropy mixing
        for i, bit in enumerate(input_bits[:num_qubits]):
            if bit == "1":
                qc.z(qr[i])

        qc.measure(qr, cr)

        simulator = Aer.get_backend("qasm_simulator")
        shots = max(1024, (self.bits // num_qubits + 1) * 100)

        if self.seed is not None:
            job = simulator.run(qc, shots=shots, seed_simulator=self.seed)
        else:
            job = simulator.run(qc, shots=shots)

        result = job.result()
        counts = result.get_counts(qc)

        # FIX: build a pool of all individual shot outcomes and sample randomly
        # from them instead of sorting by frequency. The original code sorted
        # measurements by descending count and concatenated them in that order,
        # producing a deterministic, frequency-biased bitstring that wasn't
        # random at all.
        shot_pool: List[str] = []
        for measurement, count in counts.items():
            # Qiskit measurement keys may contain spaces between register groups;
            # strip spaces so we get a clean bitstring.
            clean = measurement.replace(" ", "")
            shot_pool.extend([clean] * count)

        rng = random.Random(self.seed)  # seeded local RNG for reproducibility
        rng.shuffle(shot_pool)

        bitstring = "".join(shot_pool)

        # FIX: pad by repeating individual characters, not by doubling the whole
        # string. Doubling causes exponential overshoot and severe repetition patterns.
        if len(bitstring) < self.bits:
            pad_src = bitstring or "0"
            while len(bitstring) < self.bits:
                bitstring += pad_src[len(bitstring) % len(pad_src)]

        bitstring = bitstring[: self.bits]

        # XOR-mix with input to tie the cascade stages together
        mixed = "".join(
            str(int(a) ^ int(b))
            for a, b in zip(bitstring, input_bits.ljust(self.bits, "0")[: self.bits])
        )
        bitstring = mixed

        self.log(f"Qiskit output ({len(bitstring)} bits): {bitstring}")
        self.log(f"Qiskit hex: {hex(int(bitstring, 2))}")

        return bitstring

    def cirq_stage(self, input_bits: str) -> str:
        """Stage 3: Process through Cirq quantum circuit"""
        self.log("Stage 3: Cirq quantum circuit")

        seed_value = int(input_bits, 2) if input_bits else 0
        num_qubits = max(1, min(self.bits, (seed_value % 15) + 1))

        self.log(f"Creating Cirq circuit with {num_qubits} qubits")

        qubits = [cirq.LineQubit(i) for i in range(num_qubits)]
        circuit = cirq.Circuit()

        for qubit in qubits:
            circuit.append(cirq.H(qubit))

        for i, bit in enumerate(input_bits[:num_qubits]):
            if bit == "1":
                circuit.append(cirq.X(qubits[i]))
                circuit.append(cirq.H(qubits[i]))

        circuit.append(cirq.measure(*qubits, key="result"))

        simulator = cirq.Simulator()
        repetitions = max(1024, (self.bits // num_qubits + 1) * 100)

        # FIX: the original code had an if/else with identical bodies, so the
        # seed was silently ignored in the Cirq stage. Pass seed when provided.
        if self.seed is not None:
            result = simulator.run(circuit, repetitions=repetitions, seed=self.seed)
        else:
            result = simulator.run(circuit, repetitions=repetitions)

        measurements = result.measurements["result"]

        # FIX: same random-sampling fix as Qiskit stage — collect all rows
        # then shuffle rather than taking them in order.
        shot_pool: List[str] = []
        for measurement in measurements:
            shot_pool.append("".join(str(int(b)) for b in measurement))

        rng = random.Random(self.seed)
        rng.shuffle(shot_pool)

        bitstring = "".join(shot_pool)

        # FIX: pad without exponential string doubling
        if len(bitstring) < self.bits:
            pad_src = bitstring or "0"
            while len(bitstring) < self.bits:
                bitstring += pad_src[len(bitstring) % len(pad_src)]

        bitstring = bitstring[: self.bits]

        # XOR-mix with input to properly chain the cascade
        mixed = "".join(
            str(int(a) ^ int(b))
            for a, b in zip(bitstring, input_bits.ljust(self.bits, "0")[: self.bits])
        )
        bitstring = mixed

        self.log(f"Cirq output ({len(bitstring)} bits): {bitstring}")
        self.log(f"Cirq hex: {hex(int(bitstring, 2))}")

        return bitstring

    def generate(self, cascade: List[str]) -> str:
        """Generate random bits through the specified cascade"""
        # FIX: validate cascade is not empty before running
        if not cascade:
            raise ValueError("Cascade must contain at least one stage")

        valid_stages = {"openssl", "qiskit", "cirq"}
        for stage in cascade:
            if stage not in valid_stages:
                raise ValueError(
                    f"Invalid cascade stage: {stage!r}. Must be one of {valid_stages}"
                )

        # FIX: initialise bitstring to a proper default so it is never None.
        # The original returned None for an empty cascade (now caught above), but
        # also left bitstring=None if the first stage somehow produced no output.
        bitstring: str = "0" * self.bits

        for stage in cascade:
            if stage == "openssl":
                bitstring = self.openssl_stage()
            elif stage == "qiskit":
                bitstring = self.qiskit_stage(bitstring)
            elif stage == "cirq":
                bitstring = self.cirq_stage(bitstring)

        return bitstring


def main() -> None:
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="trio-rng: Triple-Cascade Quantum Random Number Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  trio-rng --bits 64
  trio-rng --bits 128 --cascade openssl,qiskit,cirq
  trio-rng --bits 32 --cascade qiskit,cirq --verbose
  trio-rng --bits 64 --seed 12345 --verbose
        """,
    )

    parser.add_argument(
        "--bits",
        "-b",
        type=int,
        default=64,
        help="Number of random bits to generate (default: 64)",
    )

    parser.add_argument(
        "--cascade",
        "-c",
        type=str,
        default="openssl,qiskit,cirq",
        help="Comma-separated cascade stages (default: openssl,qiskit,cirq)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show intermediate outputs from each stage",
    )

    parser.add_argument(
        "--seed",
        "-s",
        type=int,
        default=None,
        help="Seed for reproducible random generation",
    )

    args = parser.parse_args()

    # FIX: validate --bits early with a clear message
    if args.bits < 1:
        parser.error("--bits must be >= 1")

    cascade = [stage.strip().lower() for stage in args.cascade.split(",") if stage.strip()]

    # FIX: catch empty cascade from blank/comma-only input
    if not cascade:
        parser.error("--cascade must contain at least one valid stage")

    try:
        rng = TrioRNG(bits=args.bits, verbose=args.verbose, seed=args.seed)

        if args.verbose:
            print(f"\n{'='*60}")
            print("Triple-Cascade Quantum RNG")
            print(f"{'='*60}")
            print(f"Bits requested: {args.bits}")
            print(f"Cascade: {' -> '.join(cascade)}")
            if args.seed is not None:
                print(f"Seed: {args.seed}")
            print(f"{'='*60}\n")

        result = rng.generate(cascade)

        if args.verbose:
            print(f"\n{'='*60}")
            print("FINAL OUTPUT")
            print(f"{'='*60}")

        print(f"Binary: {result}")
        print(f"Hex:    {hex(int(result, 2))}")
        print(f"Dec:    {int(result, 2)}")

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
