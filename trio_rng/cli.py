#!/usr/bin/env python3
"""
trio-rng: Triple-Cascade Quantum Random Number Generator
Uses OpenSSL -> Qiskit -> Cirq cascade for random number generation
"""

import os
import sys
import argparse
import hashlib
from typing import List, Tuple

try:
    from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
    from qiskit_aer import Aer
except ImportError:
    print("Error: qiskit and qiskit-aer are required. Install with: pip install qiskit qiskit-aer", file=sys.stderr)
    sys.exit(1)

try:
    import cirq
except ImportError:
    print("Error: cirq is required. Install with: pip install cirq", file=sys.stderr)
    sys.exit(1)


class TrioRNG:
    """Triple-cascade random number generator using OpenSSL, Qiskit, and Cirq"""
    
    def __init__(self, bits: int, verbose: bool = False, seed: int = None):
        self.bits = bits
        self.verbose = verbose
        self.seed = seed
        
    def log(self, message: str):
        """Print verbose output if enabled"""
        if self.verbose:
            print(f"[VERBOSE] {message}")
    
    def openssl_stage(self) -> str:
        """Stage 1: Generate random bits using OpenSSL (os.urandom)"""
        self.log("Stage 1: OpenSSL random generation")
        
        # Calculate bytes needed
        num_bytes = (self.bits + 7) // 8
        
        if self.seed is not None:
            # Use seed for reproducibility
            self.log(f"Using seed: {self.seed}")
            # Create deterministic "random" bytes from seed
            h = hashlib.sha256(str(self.seed).encode())
            random_bytes = h.digest()
            # Extend if needed
            while len(random_bytes) < num_bytes:
                h = hashlib.sha256(random_bytes)
                random_bytes += h.digest()
            random_bytes = random_bytes[:num_bytes]
        else:
            # Use true random from OS
            random_bytes = os.urandom(num_bytes)
        
        # Convert to binary string
        bitstring = ''.join(format(byte, '08b') for byte in random_bytes)
        bitstring = bitstring[:self.bits]  # Trim to exact length
        
        self.log(f"OpenSSL output ({len(bitstring)} bits): {bitstring}")
        self.log(f"OpenSSL hex: {hex(int(bitstring, 2))}")
        
        return bitstring
    
    def qiskit_stage(self, input_bits: str) -> str:
        """Stage 2: Process through Qiskit quantum circuit"""
        self.log("Stage 2: Qiskit quantum circuit")
        
        # Use input to determine number of qubits (minimum 1, max based on input)
        seed_value = int(input_bits, 2) if input_bits else 0
        num_qubits = max(1, min(self.bits, (seed_value % 10) + 1))
        
        self.log(f"Creating Qiskit circuit with {num_qubits} qubits")
        
        # Create quantum circuit
        qr = QuantumRegister(num_qubits, 'q')
        cr = ClassicalRegister(num_qubits, 'c')
        qc = QuantumCircuit(qr, cr)
        
        # Apply Hadamard gates to create superposition
        for i in range(num_qubits):
            qc.h(qr[i])
        
        # Use input bits to add phase shifts (for more entropy mixing)
        for i, bit in enumerate(input_bits[:num_qubits]):
            if bit == '1':
                qc.z(qr[i])
        
        # Measure all qubits
        qc.measure(qr, cr)
        
        # Execute on local simulator
        simulator = Aer.get_backend('qasm_simulator')
        
        # Determine number of shots to get desired bits
        shots = max(1024, (self.bits // num_qubits + 1) * 100)
        
        if self.seed is not None:
            job = simulator.run(qc, shots=shots, seed_simulator=self.seed)
        else:
            job = simulator.run(qc, shots=shots)
        
        result = job.result()
        counts = result.get_counts(qc)
        
        # Extract random bits from measurements
        # Sort by count and take measurements to build bitstring
        sorted_results = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        
        bitstring = ""
        for measurement, _ in sorted_results:
            bitstring += measurement
            if len(bitstring) >= self.bits:
                break
        
        bitstring = bitstring[:self.bits]
        
        # If we don't have enough bits, repeat
        while len(bitstring) < self.bits:
            bitstring += bitstring
        
        bitstring = bitstring[:self.bits]
        
        self.log(f"Qiskit output ({len(bitstring)} bits): {bitstring}")
        self.log(f"Qiskit hex: {hex(int(bitstring, 2))}")
        
        return bitstring
    
    def cirq_stage(self, input_bits: str) -> str:
        """Stage 3: Process through Cirq quantum circuit"""
        self.log("Stage 3: Cirq quantum circuit")
        
        # Use input to determine number of qubits
        seed_value = int(input_bits, 2) if input_bits else 0
        num_qubits = max(1, min(self.bits, (seed_value % 15) + 1))
        
        self.log(f"Creating Cirq circuit with {num_qubits} qubits")
        
        # Create qubits
        qubits = [cirq.LineQubit(i) for i in range(num_qubits)]
        
        # Create circuit
        circuit = cirq.Circuit()
        
        # Apply Hadamard gates
        for qubit in qubits:
            circuit.append(cirq.H(qubit))
        
        # Use input bits to add X gates (bit flip based on input)
        for i, bit in enumerate(input_bits[:num_qubits]):
            if bit == '1':
                circuit.append(cirq.X(qubits[i]))
                circuit.append(cirq.H(qubits[i]))
        
        # Measure
        circuit.append(cirq.measure(*qubits, key='result'))
        
        # Simulate
        simulator = cirq.Simulator()
        
        # Determine repetitions needed
        repetitions = max(1024, (self.bits // num_qubits + 1) * 100)
        
        if self.seed is not None:
            result = simulator.run(circuit, repetitions=repetitions)
        else:
            result = simulator.run(circuit, repetitions=repetitions)
        
        # Extract bits from measurements
        measurements = result.measurements['result']
        
        bitstring = ""
        for measurement in measurements:
            bits = ''.join(str(int(b)) for b in measurement)
            bitstring += bits
            if len(bitstring) >= self.bits:
                break
        
        bitstring = bitstring[:self.bits]
        
        # Ensure we have enough bits
        while len(bitstring) < self.bits:
            bitstring += bitstring
        
        bitstring = bitstring[:self.bits]
        
        self.log(f"Cirq output ({len(bitstring)} bits): {bitstring}")
        self.log(f"Cirq hex: {hex(int(bitstring, 2))}")
        
        return bitstring
    
    def generate(self, cascade: List[str]) -> str:
        """Generate random bits through the specified cascade"""
        bitstring = None
        
        # Validate cascade
        valid_stages = {'openssl', 'qiskit', 'cirq'}
        for stage in cascade:
            if stage not in valid_stages:
                raise ValueError(f"Invalid cascade stage: {stage}. Must be one of {valid_stages}")
        
        # Execute cascade
        for stage in cascade:
            if stage == 'openssl':
                bitstring = self.openssl_stage()
            elif stage == 'qiskit':
                if bitstring is None:
                    bitstring = '0' * self.bits  # Default input if first stage
                bitstring = self.qiskit_stage(bitstring)
            elif stage == 'cirq':
                if bitstring is None:
                    bitstring = '0' * self.bits  # Default input if first stage
                bitstring = self.cirq_stage(bitstring)
        
        return bitstring


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='trio-rng: Triple-Cascade Quantum Random Number Generator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  quantum-rng --bits 64
  quantum-rng --bits 128 --cascade openssl,qiskit,cirq
  quantum-rng --bits 32 --cascade qiskit,cirq --verbose
  quantum-rng --bits 64 --seed 12345 --verbose
        """
    )
    
    parser.add_argument(
        '--bits', '-b',
        type=int,
        default=64,
        help='Number of random bits to generate (default: 64)'
    )
    
    parser.add_argument(
        '--cascade', '-c',
        type=str,
        default='openssl,qiskit,cirq',
        help='Comma-separated cascade stages (default: openssl,qiskit,cirq)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show intermediate outputs from each stage'
    )
    
    parser.add_argument(
        '--seed', '-s',
        type=int,
        default=None,
        help='Seed for reproducible random generation'
    )
    
    args = parser.parse_args()
    
    # Parse cascade
    cascade = [stage.strip().lower() for stage in args.cascade.split(',')]
    
    try:
        # Create RNG
        rng = TrioRNG(bits=args.bits, verbose=args.verbose, seed=args.seed)
        
        # Generate random bits
        if args.verbose:
            print(f"\n{'='*60}")
            print(f"Triple-Cascade Quantum RNG")
            print(f"{'='*60}")
            print(f"Bits requested: {args.bits}")
            print(f"Cascade: {' -> '.join(cascade)}")
            if args.seed is not None:
                print(f"Seed: {args.seed}")
            print(f"{'='*60}\n")
        
        result = rng.generate(cascade)
        
        # Output results
        if args.verbose:
            print(f"\n{'='*60}")
            print(f"FINAL OUTPUT")
            print(f"{'='*60}")
        
        print(f"Binary: {result}")
        print(f"Hex:    {hex(int(result, 2))}")
        print(f"Dec:    {int(result, 2)}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
