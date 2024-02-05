from PIL import Image, ImageDraw
import os

def get_user_input(prompt, options):
    while True:
        input_value = input(prompt)
        if input_value in options:
            return options[input_value]
        print("Invalid input. Please try again.")

def add_bar(draw, x, y, thick, height=50):
    width = 8 if thick else 4
    draw.rectangle([x, y, x + width, y + height], fill="black")
    return x + width

def generate_barcode(code, img_path):
    bars = [
        [0, 0, 1, 1, 0], [1, 0, 0, 0, 1], [0, 1, 0, 0, 1], [1, 1, 0, 0, 0],
        [0, 0, 1, 0, 1], [1, 0, 1, 0, 0], [0, 1, 1, 0, 0], [0, 0, 0, 1, 1],
        [1, 0, 0, 1, 0], [0, 1, 0, 1, 0]
    ]

    img = Image.new('1', (200, 50), "white")
    draw = ImageDraw.Draw(img)
    x = 10  # Start with a margin

    # Simplified pattern addition
    def add_pattern(sequence):
        nonlocal x
        for thick in sequence:
            x = add_bar(draw, x, 0, thick) + 4  # Adding space after each bar directly

    # Run-in pattern
    add_pattern([0, 0, 0])

    # Barcode generation
    for digit in code:
        for thick in bars[int(digit)]:
            x = add_bar(draw, x, 0, thick) + 4

    # Run-out pattern
    add_pattern([1, 0, 1])

    img.save(img_path)
    print(f"Barcode generated and saved as {img_path}")

def calculate_check_digit(code):
    sum_ = sum(int(digit) * (3 if idx % 2 == 0 else 1) for idx, digit in enumerate(code))
    return (10 - sum_ % 10) % 10

def main():
    # Using dictionary comprehensions to simplify options creation
    options = {
        "temperature": {"0": "00", "1": "01", "2": "10", "3": "11"},
        "size": {"0": "0", "1": "1"},
        "charge": {"0": "00", "1": "01", "2": "10", "3": "11"},
        "volume": {str(i): format(i, '04b') for i in range(16)},
        "flow_rate": {str(i): format(i, '03b') for i in range(8)},
        "purge": {"0": "00", "1": "01", "2": "10", "3": "11"},
        "misc": {"0": "", "1": "1", "2": "11"},
    }

    prompts = {
        "temperature": "Enter Water Temperature (0=cold, 1=warm, 2=83°C, 3=93°C): ",
        "size": "Enter Size (0=Standard, 1=Large): ",
        "charge": "Enter Cartridge Charge (0=fast with soak, 1=fast without soak, 2=slow with soak, 3=slow without soak): ",
        "volume": "Enter Beverage Volume (0=50ml, ..., 15=300ml): ",
        "flow_rate": "Enter Flow Rate (0=30%, ..., 7=100%): ",
        "purge": "Enter Purge (0=slow/short, 1=slow/long, 2=fast/short, 3=fast/long): ",
        "misc": "Enter Misc: 0, 1 or 2"
    }

    decimal_prepend_zero = ''

    # Collecting user inputs
    inputs = {key: get_user_input(prompts[key], options[key]) for key in prompts}
    binary_string = ''.join(inputs[key] for key in reversed(['misc','purge', 'flow_rate', 'volume', 'charge', 'size', 'temperature']))

    print(f"Binary String before padding: {binary_string}")

    # Padding
    if int(binary_string, 2) < 1000:
        binary_with_padding = '1' + binary_string.rjust(17 - 1, '0')
    else:
        binary_with_padding = binary_string.rjust(17, '0')

    print(f"Binary String after padding: {binary_with_padding}")
        
    # Trimming and determining decimal_prepend_zero
    if binary_with_padding.startswith('00'):
        decimal_prepend_zero = '0' if not binary_with_padding.endswith('1') else ''
        min_length = max(len(binary_with_padding) - 2, 16)
        for i in range(len(binary_with_padding) - 1, min_length - 1, -1):
            if binary_with_padding[i] == '0':
                binary_with_padding = binary_with_padding[:i]
            else:
                break

    print(f"Binary String after Trim: {binary_with_padding}")

    # Convert to decimal and prepend '0' if necessary
    decimal_value = str(int(binary_with_padding, 2))
    decimal_value_after_prepend = decimal_prepend_zero + decimal_value

    # Calculate check digit and append
    decimal_check_digit = calculate_check_digit(decimal_value_after_prepend)
    decimal_str_with_check = decimal_value_after_prepend + str(decimal_check_digit)

    print(f"Decimal Value: {decimal_value}")
    print(f"Decimal With Pad: {decimal_value_after_prepend}")
    print(f"Decimal Value w/ Check Bit: {decimal_str_with_check}")

    # Barcode generation
    img_path = os.path.join(os.getcwd(), f"barcode_{decimal_str_with_check}.png")
    generate_barcode(decimal_str_with_check, img_path)

if __name__ == "__main__":
    main()
