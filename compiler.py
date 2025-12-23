#!/usr/bin/env python3
"""
DuckyScript Compiler
Compiles DuckyScript (.txt) to inject.bin for USB Rubber Ducky

Binary format:
- Each instruction is 2 bytes: [modifier, keycode]
- Delays: [0x00, delay_value] where delay is ms (max 255 per chunk)
- Modifiers: 0x00=none, 0x01=ctrl, 0x02=shift, 0x04=alt, 0x08=gui/cmd
"""

import sys
import os

# HID Keycodes
KEYCODES = {
    'a': 0x04, 'b': 0x05, 'c': 0x06, 'd': 0x07, 'e': 0x08, 'f': 0x09,
    'g': 0x0a, 'h': 0x0b, 'i': 0x0c, 'j': 0x0d, 'k': 0x0e, 'l': 0x0f,
    'm': 0x10, 'n': 0x11, 'o': 0x12, 'p': 0x13, 'q': 0x14, 'r': 0x15,
    's': 0x16, 't': 0x17, 'u': 0x18, 'v': 0x19, 'w': 0x1a, 'x': 0x1b,
    'y': 0x1c, 'z': 0x1d,
    '1': 0x1e, '2': 0x1f, '3': 0x20, '4': 0x21, '5': 0x22,
    '6': 0x23, '7': 0x24, '8': 0x25, '9': 0x26, '0': 0x27,
    ',': 0x36, '.': 0x37, '/': 0x38, ';': 0x33, "'": 0x34,
    '[': 0x2f, ']': 0x30, '\\': 0x31, '-': 0x2d, '=': 0x2e,
    '`': 0x35, ' ': 0x2c,
}

# Shifted characters
SHIFT_CHARS = {
    'A': 0x04, 'B': 0x05, 'C': 0x06, 'D': 0x07, 'E': 0x08, 'F': 0x09,
    'G': 0x0a, 'H': 0x0b, 'I': 0x0c, 'J': 0x0d, 'K': 0x0e, 'L': 0x0f,
    'M': 0x10, 'N': 0x11, 'O': 0x12, 'P': 0x13, 'Q': 0x14, 'R': 0x15,
    'S': 0x16, 'T': 0x17, 'U': 0x18, 'V': 0x19, 'W': 0x1a, 'X': 0x1b,
    'Y': 0x1c, 'Z': 0x1d,
    '!': 0x1e, '@': 0x1f, '#': 0x20, '$': 0x21, '%': 0x22,
    '^': 0x23, '&': 0x24, '*': 0x25, '(': 0x26, ')': 0x27,
    '<': 0x36, '>': 0x37, '?': 0x38, ':': 0x33, '"': 0x34,
    '{': 0x2f, '}': 0x30, '|': 0x31, '_': 0x2d, '+': 0x2e,
    '~': 0x35,
}

# Special keys
SPECIAL_KEYS = {
    'ENTER': 0x28, 'RETURN': 0x28,
    'ESCAPE': 0x29, 'ESC': 0x29,
    'BACKSPACE': 0x2a, 'BSPACE': 0x2a,
    'TAB': 0x2b,
    'SPACE': 0x2c,
    'CAPSLOCK': 0x39,
    'F1': 0x3a, 'F2': 0x3b, 'F3': 0x3c, 'F4': 0x3d, 'F5': 0x3e, 'F6': 0x3f,
    'F7': 0x40, 'F8': 0x41, 'F9': 0x42, 'F10': 0x43, 'F11': 0x44, 'F12': 0x45,
    'PRINTSCREEN': 0x46,
    'SCROLLLOCK': 0x47,
    'PAUSE': 0x48, 'BREAK': 0x48,
    'INSERT': 0x49,
    'HOME': 0x4a,
    'PAGEUP': 0x4b,
    'DELETE': 0x4c, 'DEL': 0x4c,
    'END': 0x4d,
    'PAGEDOWN': 0x4e,
    'RIGHT': 0x4f, 'RIGHTARROW': 0x4f,
    'LEFT': 0x50, 'LEFTARROW': 0x50,
    'DOWN': 0x51, 'DOWNARROW': 0x51,
    'UP': 0x52, 'UPARROW': 0x52,
    'NUMLOCK': 0x53,
    'APP': 0x65, 'MENU': 0x65,
}

# Modifiers
MOD_NONE  = 0x00
MOD_CTRL  = 0x01
MOD_SHIFT = 0x02
MOD_ALT   = 0x04
MOD_GUI   = 0x08  # Windows/Command key


def encode_delay(ms):
    """Encode delay in milliseconds. Returns list of byte pairs."""
    result = []
    while ms > 0:
        chunk = min(ms, 255)
        result.extend([0x00, chunk])  # Delay format: [0x00, value]
        ms -= chunk
    return result


def encode_char(char):
    """Encode a single character. Returns [keycode, modifier] (swapped for new ducky)."""
    if char in KEYCODES:
        return [KEYCODES[char], MOD_NONE]  # [keycode, modifier]
    elif char in SHIFT_CHARS:
        return [SHIFT_CHARS[char], MOD_SHIFT]  # [keycode, modifier]
    else:
        # Unknown character, skip
        print(f"Warning: Unknown character '{char}' (0x{ord(char):02x}), skipping")
        return []


def encode_string(text):
    """Encode a STRING command. Returns list of bytes."""
    result = []
    for char in text:
        result.extend(encode_char(char))
    return result


def get_key_code(key_name):
    """Get keycode for a key name (case insensitive)."""
    key_upper = key_name.upper()
    if key_upper in SPECIAL_KEYS:
        return SPECIAL_KEYS[key_upper]
    key_lower = key_name.lower()
    if key_lower in KEYCODES:
        return KEYCODES[key_lower]
    if key_name in SHIFT_CHARS:
        return SHIFT_CHARS[key_name]
    return None


def parse_modifier_combo(line):
    """Parse a line with modifiers like 'CTRL ALT DELETE' or 'COMMAND SPACE'."""
    parts = line.split()
    modifier = MOD_NONE
    keycode = None

    for part in parts:
        part_upper = part.upper()
        if part_upper in ('CTRL', 'CONTROL'):
            modifier |= MOD_CTRL
        elif part_upper in ('SHIFT'):
            modifier |= MOD_SHIFT
        elif part_upper in ('ALT', 'OPTION'):
            modifier |= MOD_ALT
        elif part_upper in ('GUI', 'WINDOWS', 'COMMAND', 'CMD', 'META'):
            modifier |= MOD_GUI
        else:
            # This should be the key
            keycode = get_key_code(part)
            if keycode is None:
                print(f"Warning: Unknown key '{part}'")

    if keycode is not None:
        return [keycode, modifier]  # [keycode, modifier]
    elif modifier != MOD_NONE:
        # Just modifier pressed (like just GUI key)
        return [0x00, modifier]  # [keycode, modifier]
    return []


def compile_script(input_path, output_path):
    """Compile a DuckyScript file to inject.bin."""
    payload = []
    default_delay = 0

    with open(input_path, 'r') as f:
        lines = f.readlines()

    for line_num, line in enumerate(lines, 1):
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith('REM') or line.startswith('//'):
            continue

        # Add default delay between commands if set
        if default_delay > 0 and payload:
            payload.extend(encode_delay(default_delay))

        try:
            if line.startswith('DEFAULT_DELAY') or line.startswith('DEFAULTDELAY'):
                default_delay = int(line.split()[1])

            elif line.startswith('DELAY'):
                delay_ms = int(line.split()[1])
                payload.extend(encode_delay(delay_ms))

            elif line.startswith('STRING '):
                text = line[7:]  # Everything after "STRING "
                payload.extend(encode_string(text))

            elif line.startswith('STRINGLN '):
                text = line[9:]  # Everything after "STRINGLN "
                payload.extend(encode_string(text))
                payload.extend([SPECIAL_KEYS['ENTER'], MOD_NONE])  # [keycode, modifier]

            # Single special keys
            elif line in SPECIAL_KEYS:
                payload.extend([SPECIAL_KEYS[line], MOD_NONE])  # [keycode, modifier]

            # Modifier combinations (CTRL, ALT, GUI/COMMAND, SHIFT + key)
            elif any(line.upper().startswith(mod) for mod in
                    ['CTRL', 'CONTROL', 'ALT', 'SHIFT', 'GUI', 'WINDOWS', 'COMMAND', 'CMD']):
                result = parse_modifier_combo(line)
                if result:
                    payload.extend(result)

            # REPEAT command (repeat last instruction)
            elif line.startswith('REPEAT') or line.startswith('REPLAY'):
                count = int(line.split()[1]) if len(line.split()) > 1 else 1
                if len(payload) >= 2:
                    last_instruction = payload[-2:]
                    for _ in range(count):
                        payload.extend(last_instruction)

            else:
                print(f"Warning: Line {line_num}: Unknown command '{line}'")

        except Exception as e:
            print(f"Error on line {line_num}: {e}")
            continue

    # Write binary output
    with open(output_path, 'wb') as f:
        f.write(bytes(payload))

    print(f"Compiled {len(payload)} bytes to {output_path}")
    return len(payload)


def main():
    if len(sys.argv) < 2:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        input_file = os.path.join(script_dir, 'inject.txt')
        output_file = os.path.join(script_dir, 'inject.bin')
    elif len(sys.argv) == 2:
        input_file = sys.argv[1]
        output_file = os.path.splitext(input_file)[0] + '.bin'
    else:
        input_file = sys.argv[1]
        output_file = sys.argv[2]

    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found")
        sys.exit(1)

    print(f"Compiling: {input_file}")
    compile_script(input_file, output_file)
    print("Done!")


if __name__ == '__main__':
    main()
