# Contributing to Slot Car Relay Controller

Thank you for considering contributing to this project! 🎉

## How to Contribute

### Reporting Bugs

If you find a bug, please open an issue with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Your hardware setup (Raspberry Pi model, relay module)
- Logs from `sudo journalctl -u smartrace-relay.service -n 100`

### Suggesting Features

Feature requests are welcome! Please open an issue describing:
- What problem does it solve?
- How should it work?
- Any implementation ideas?

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes**
   - Follow PEP 8 style guide
   - Add comments for complex logic
   - Test on actual hardware
4. **Commit your changes**
   ```bash
   git commit -m "Add amazing feature"
   ```
5. **Push to your fork**
   ```bash
   git push origin feature/amazing-feature
   ```
6. **Open a Pull Request**

### Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/slot-car-relay-controller.git
cd slot-car-relay-controller

# Test your changes
sudo python3 smartrace_relay.py

# Run syntax check
python3 -m py_compile smartrace_relay.py
```

### Testing Checklist

Before submitting a PR, please verify:
- [ ] Code follows PEP 8 style guide
- [ ] Tested on actual Raspberry Pi hardware
- [ ] Both relays trigger correctly
- [ ] Web interface loads and functions
- [ ] SmartRace integration works
- [ ] No syntax errors
- [ ] Documentation updated if needed

### Code Style

- Use 4 spaces for indentation
- Maximum line length: 100 characters
- Use descriptive variable names
- Add docstrings for functions
- Comment complex logic

### Questions?

Feel free to open an issue for any questions about contributing!

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
