from PIL import Image, ImageDraw
import os

def get_user_input(prompt: str, options: dict) -> str:
    """
    Prompt the user until a valid input is provided.

    Parameters:
        prompt (str): The prompt message to display.
        options (dict): A mapping of valid input strings to their corresponding values.

    Returns:
        str: The value associated with the valid user input.
    """
    while True:
        user_input = input(prompt)
        if user_input in options:
            return options[user_input]
        print("Invalid input. Please try again.")

def add_bar(draw: ImageDraw.Draw, x: int, y: int, thick: int, height: int = 50) -> int:
    """
    Draw a vertical bar on the image.

    Parameters:
        draw (ImageDraw.Draw): The drawing context.
        x (int): The starting x-coordinate.
        y (int): The starting y-coordinate.
        thick (int): Thickness flag (non-zero means thick, zero means thin).
        height (int, optional): The height of the bar. Defaults to 50.

    Returns:
        int: The new x-coordinate after drawing the bar.
    """
    width = 8 if thick else 4
    draw.rectangle([x, y, x + width, y + height], fill="black")
    return x + width

def generate_barcode(code: str, img_path: str) -> None:
    """
    Generate a barcode image from a given code and save it.

    The barcode is created by drawing a series of vertical bars based on a lookup
    table and adding a run-in and run-out pattern.

    Parameters:
        code (str): The numeric code (with check digit) used to create the barcode.
        img_path (str): The file path to save the generated barcode image.
    """
    # Lookup table for digit to bar pattern mapping
    bars = [
        [0, 0, 1, 1, 0],
        [1, 0, 0, 0, 1],
        [0, 1, 0, 0, 1],
        [1, 1, 0, 0, 0],
        [0, 0, 1, 0, 1],
        [1, 0, 1, 0, 0],
        [0, 1, 1, 0, 0],
        [0, 0, 0, 1, 1],
        [1, 0, 0, 1, 0],
        [0, 1, 0, 1, 0]
    ]

    img_width, img_height = 200, 50
    img = Image.new('1', (img_width, img_height), "white")
    draw = ImageDraw.Draw(img)
    x = 10  # Starting margin

    def add_pattern(sequence: list) -> None:
        nonlocal x
        # For each pattern element, draw a bar and add spacing after it.
        for thick in sequence:
            x = add_bar(draw, x, 0, thick) + 4

    # Draw the run-in pattern (start marker)
    add_pattern([0, 0, 0])

    # Draw the barcode based on each digit of the code.
    for digit in code:
        index = int(digit)
        # Ensure the digit is between 0 and 9 before accessing the lookup table.
        if 0 <= index < len(bars):
            for thick in bars[index]:
                x = add_bar(draw, x, 0, thick) + 4

    # Draw the run-out pattern (end marker)
    add_pattern([1, 0, 1])

    img.save(img_path)
    print(f"Barcode generated and saved as {img_path}")

def calculate_check_digit(code: str) -> int:
    """
    Calculate the check digit using a weighted sum algorithm.

    For each digit in the code, multiply by 3 if its index is even, or by 1 if odd.
    Then, the check digit is (10 - (sum mod 10)) mod 10.

    Parameters:
        code (str): The numeric code as a string.

    Returns:
        int: The computed check digit.
    """
    total = sum(int(digit) * (3 if idx % 2 == 0 else 1) for idx, digit in enumerate(code))
    return (10 - total % 10) % 10

def main() -> None:
    """
    Main function that collects user inputs, computes the binary and decimal representations,
    calculates a check digit, and generates a barcode image.
    """
    # Define mapping options for each parameter
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
        "misc": "Enter Misc (0, 1 or 2): "
    }

    decimal_prepend_zero = ''

    # Collect user inputs and construct a binary string.
    user_inputs = {key: get_user_input(prompts[key], options[key]) for key in prompts}
    # Concatenate the binary parts in a specific reversed order.
    binary_string = ''.join(user_inputs[key] for key in reversed(
        ['misc', 'purge', 'flow_rate', 'volume', 'charge', 'size', 'temperature']
    ))
    print(f"Binary String before padding: {binary_string}")

    # Pad the binary string:
    # If the numeric value is less than 1000, prepend with '1' and pad to a total length of 17.
    if int(binary_string, 2) < 1000:
        binary_with_padding = '1' + binary_string.rjust(16, '0')
    else:
        binary_with_padding = binary_string.rjust(17, '0')
    print(f"Binary String after padding: {binary_with_padding}")

    # Optionally trim the binary string if it starts with '00'
    if binary_with_padding.startswith('00'):
        decimal_prepend_zero = '0' if not binary_with_padding.endswith('1') else ''
        min_length = max(len(binary_with_padding) - 2, 16)
        # Remove trailing zeros until reaching a '1' or the minimum length.
        for i in range(len(binary_with_padding) - 1, min_length - 1, -1):
            if binary_with_padding[i] == '0':
                binary_with_padding = binary_with_padding[:i]
            else:
                break
    print(f"Binary String after Trim: {binary_with_padding}")

    # Convert binary string to decimal.
    decimal_value = str(int(binary_with_padding, 2))
    decimal_value_with_pad = decimal_prepend_zero + decimal_value

    # Calculate the check digit and append it.
    check_digit = calculate_check_digit(decimal_value_with_pad)
    final_decimal_code = decimal_value_with_pad + str(check_digit)

    print(f"Decimal Value: {decimal_value}")
    print(f"Decimal With Pad: {decimal_value_with_pad}")
    print(f"Decimal Value with Check Digit: {final_decimal_code}")

    # Generate the barcode image.
    img_path = os.path.join(os.getcwd(), f"barcode_{final_decimal_code}.png")
    generate_barcode(final_decimal_code, img_path)

if __name__ == "__main__":
    main()
