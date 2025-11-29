# trio-rng: Triple-Cascade Quantum Random Number Generator

A Python CLI tool that generates cryptographically secure random numbers using a triple-cascade design combining OpenSSL, Qiskit quantum circuits, and Cirq quantum circuits.

## Current Features

### Core Functionality
✅ **Triple-Cascade Random Generation**
- Stage 1: OpenSSL cryptographic random (`os.urandom`)
- Stage 2: Qiskit quantum circuit simulation with Hadamard gates
- Stage 3: Cirq quantum circuit simulation with Hadamard gates

✅ **Flexible Cascade Configuration**
- Choose any combination: `--cascade openssl`, `--cascade qiskit,cirq`, or full cascade
- Each stage feeds its output to the next stage

✅ **Multiple Output Formats**
- Binary (bitstring)
- Hexadecimal
- Decimal (integer)

✅ **Offline Operation**
- Uses local Qiskit Aer simulator
- Uses local Cirq simulator
- No internet or quantum hardware required

✅ **Reproducible Generation**
- `--seed` option for deterministic output
- Perfect for testing and debugging

✅ **Verbose Debug Mode**
- `--verbose` shows intermediate outputs from each stage
- See the cascade in action with detailed logging

### Command-Line Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--bits` | `-b` | Number of random bits to generate | 64 |
| `--cascade` | `-c` | Comma-separated stages (openssl,qiskit,cirq) | All three |
| `--verbose` | `-v` | Show intermediate outputs | Off |
| `--seed` | `-s` | Seed for reproducible generation | None |

### What It Does

1. **Generates random bits** using quantum circuit simulation
2. **Cascades entropy** through three stages for enhanced randomness
3. **Outputs in multiple formats** (binary, hex, decimal)
4. **Works offline** with local simulators only
5. **Supports reproducibility** via seed parameter

## Installation

### Prerequisites

- Python 3.8 or higher
- Python venv module (for virtual environments)

### Actual Installation Steps (Tested on Debian/Ubuntu)

```bash
# 1. Download and extract trio-rng or run the setup script
bash trio_rng_complete.sh

# 2. Install python3-venv if you don't have it
sudo apt install python3.12-venv  # or python3-venv

# 3. Create a virtual environment
python3 -m venv ~/trio-rng-env

# 4. Activate the virtual environment
source ~/trio-rng-env/bin/activate

# 5. Navigate to the package directory
cd trio-rng

# 6. Install the package
pip install -e .

# 7. Now you can use quantum-rng from anywhere (while venv is active)
trio-rng --bits 64 --verbose
```

### Important Notes

- **Linux users**: Modern Debian/Ubuntu systems require virtual environments (PEP 668)
- **Don't use** `--break-system-packages` - it can damage your system Python
- **Each time you use it**: Activate the venv with `source ~/trio-rng-env/bin/activate`
- **To deactivate**: Run `deactivate` when done

### Alternative: Run Without Installation

```bash
cd trio-rng
python3 trio_rng/cli.py --bits 64 --verbose
```

## Project Structure

```
trio-rng/
├── trio_rng/
│   ├── __init__.py
│   └── cli.py          # Main CLI implementation
├── setup.py            # Package setup
├── README.md           # This file
└── requirements.txt    # Dependencies
```

## Usage Examples

### Basic Usage

Activate your virtual environment first:
```bash
source ~/trio-rng-env/bin/activate
```

Generate 64 random bits using all three stages:
```bash
trio-rng --bits 64
```

Output:
```
Binary: 0001010101000100101100110100000010000101010001100100001000110001
Hex:    0x1544b34085464231
Dec:    1532546862908064305
```

### Specify Cascade Stages

Use only specific stages:

```bash
# Only Qiskit and Cirq
trio-rng --bits 128 --cascade qiskit,cirq

# Only OpenSSL
trio-rng --bits 32 --cascade openssl

# All three (default)
trio-rng --bits 256 --cascade openssl,qiskit,cirq
```

### Verbose Mode

See intermediate outputs from each stage:

```bash
trio-rng --bits 64 --verbose
```

### Reproducible Generation

Use a seed for reproducible results:

```bash
trio-rng --bits 64 --seed 12345 --verbose
```

### Full Example

```bash
trio-rng --bits 128 --cascade openssl,qiskit,cirq --verbose --seed 42
```

## How It Works

### Stage 1: OpenSSL
- Uses `os.urandom()` to generate cryptographically secure random bytes
- Converts to binary bitstring
- With seed: Uses SHA-256 hash of seed for reproducibility

### Stage 2: Qiskit
- Creates quantum circuit with Hadamard gates on N qubits
- Uses previous stage's output to influence circuit (phase shifts)
- Measures qubits using local Aer simulator
- Produces new random bitstring

### Stage 3: Cirq
- Creates quantum circuit with Hadamard gates on N qubits
- Uses previous stage's output to influence circuit (bit flips + Hadamard)
- Measures qubits using local Cirq simulator
- Produces final random bitstring

## Output Format

The tool outputs the random number in three formats:

```
Binary: 1010110101...
Hex:    0x5af3c2...
Dec:    123456789...
```

## Common Use Cases

### Generate a random number in a specific range

Since the tool outputs large random numbers, you can map them to any range:

```bash
# Generate random number between 1 and 10
trio-rng --bits 32 | grep "Dec:" | awk '{print ($2 % 10) + 1}'

# Generate random number between 1 and 100
trio-rng --bits 32 | grep "Dec:" | awk '{print ($2 % 100) + 1}'

# Generate random number between MIN and MAX (e.g., 50 to 150)
trio-rng --bits 32 | grep "Dec:" | awk '{MIN=50; MAX=150; print ($2 % (MAX-MIN+1)) + MIN}'
```

### Use with Python

```python
import subprocess

def get_quantum_random(min_val=1, max_val=10):
    result = subprocess.run(['quantum-rng', '--bits', '32'], 
                          capture_output=True, text=True)
    for line in result.stdout.split('\n'):
        if line.startswith('Dec:'):
            num = int(line.split()[1])
            return (num % (max_val - min_val + 1)) + min_val
    return None

# Generate random number between 1 and 10
print(get_quantum_random(1, 10))
```

### Generate cryptographic keys

```bash
# 256-bit key
trio-rng --bits 256

# 128-bit key in hex
trio-rng --bits 128 | grep "Hex:"
```

## Examples

### Generate 256-bit random number
```bash
trio-rng --bits 256
```

Output:
```
Binary: 1010011010...
Hex:    0xa6f2c8...
Dec:    98765432...
```

### Compare cascade stages
```bash
# OpenSSL only
trio-rng --bits 64 --cascade openssl --seed 42

# Qiskit only  
trio-rng --bits 64 --cascade qiskit --seed 42

# Full cascade
trio-rng --bits 64 --cascade openssl,qiskit,cirq --seed 42
```

### Verbose output for debugging
```bash
trio-rng --bits 64 --verbose
```

Full Output:
```
============================================================
Triple-Cascade RNG
============================================================
Bits requested: 64
Cascade: openssl -> qiskit -> cirq
============================================================

[VERBOSE] Stage 1: OpenSSL random generation
[VERBOSE] OpenSSL output (64 bits): 0110100100011000101001100001011101100000101111000111110110100010
[VERBOSE] OpenSSL hex: 0x6918a61760bc7da2

[VERBOSE] Stage 2: Qiskit quantum circuit
[VERBOSE] Creating Qiskit circuit with 5 qubits
[VERBOSE] Qiskit output (64 bits): 0010001011000110111000000101010001001000101100101000101100011000
[VERBOSE] Qiskit hex: 0x22c6e05448b28b18

[VERBOSE] Stage 3: Cirq quantum circuit
[VERBOSE] Creating Cirq circuit with 9 qubits
[VERBOSE] Cirq output (64 bits): 0001010101000100101100110100000010000101010001100100001000110001
[VERBOSE] Cirq hex: 0x1544b34085464231

============================================================
FINAL OUTPUT
============================================================
Binary: 0001010101000100101100110100000010000101010001100100001000110001
Hex:    0x1544b34085464231
Dec:    1532546862908064305
```

## Requirements

- qiskit >= 0.45.0
- qiskit-aer >= 0.13.0
- cirq >= 1.3.0

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Security Note

While this tool uses quantum circuits for random number generation, it relies on classical simulators. For production cryptographic applications, use dedicated hardware random number generators or certified cryptographic libraries.

## Troubleshooting

### Import Errors

If you see import errors for qiskit or cirq:

```bash
pip install qiskit qiskit-aer cirq --upgrade
```

### Command Not Found

If `trio-rng` command is not found after installation:

```bash
# Reinstall in editable mode
pip install -e .

# Or check if ~/.local/bin is in your PATH
export PATH=$PATH:~/.local/bin
```

## Advanced Usage

### Python API

You can also use trio-rng as a Python library:

```python
from trio_rng.cli import TrioRNG

# Create RNG instance
rng = TrioRNG(bits=128, verbose=True, seed=42)

# Generate random bits
result = rng.generate(['openssl', 'qiskit', 'cirq'])

print(f"Binary: {result}")
print(f"Hex: {hex(int(result, 2))}")
```

## Performance

Typical generation times (on modern hardware):

- 64 bits: ~1-2 seconds
- 128 bits: ~2-4 seconds  
- 256 bits: ~4-8 seconds

Performance depends on the number of quantum simulator shots required and the complexity of the quantum circuits.


<3 JEGLY
