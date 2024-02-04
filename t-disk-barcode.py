from PIL import Image, ImageDraw
import os

def get_user_input(prompt, options):
    while True:
        input_value = input(prompt)
        if input_value in options:
            return options[input_value]
        else:
            print("Invalid input. Please try again.")

def add_bar(draw, x, y, thick):
    width = 8 if thick else 4
    draw.rectangle([x, y, x + width, y + 50], fill="black")
    return x + width

def add_space(x, thick):
    return x + (8 if thick else 4)

def generate_barcode(code, img_path):
    
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

    # Create an image
    img = Image.new('1', (200, 50), "white")
    draw = ImageDraw.Draw(img)
    x = 0

    # Run-in pattern
    x = add_bar(draw, x, 0, 0)
    x = add_space(x, 0)
    x = add_bar(draw, x, 0, 0)
    x = add_space(x, 0)

    # Generate barcode
    for i in range(0, len(code), 2):
        first_digit = int(code[i])
        second_digit = int(code[i + 1]) if i + 1 < len(code) else 0

        for j in range(5):
            x = add_bar(draw, x, 0, bars[first_digit][j])
            x = add_space(x, bars[second_digit][j])

    # Run-out pattern
    x = add_bar(draw, x, 0, 1)
    x = add_space(x, 0)
    x = add_bar(draw, x, 0, 0)

    img.save(img_path)
    print(f"Barcode generated and saved as {img_path}")

def calculate_check_digit(code):
    even_sum = sum(int(code[i]) for i in range(0, len(code), 2))
    odd_sum = sum(int(code[i]) for i in range(1, len(code), 2))
    total = (even_sum * 3) + odd_sum
    return (10 - total % 10) % 10

def reverse_bits(binary_value):
    return binary_value[::-1]

def main():

    temperature_options = {"0": "00", "1": "01", "2": "10", "3": "11"}
    size_options = {"0": "0", "1": "1"}
    charge_options = {"0": "00", "1": "01", "2": "10", "3": "11"}
    volume_options = {str(i): format(i, '04b') for i in range(16)}
    flow_rate_options = {str(i): format(i, '03b') for i in range(8)}
    purge_options = {"0": "00", "1": "01", "2": "10", "3": "11"}

    # User input collection
    temperature = get_user_input("Enter Water Temperature (0=cold, 1=warm, 2=83°C, 3=93°C): ", temperature_options)
    size = get_user_input("Enter Size (0=Standard, 1=Large): ", size_options)
    charge = get_user_input("Enter Cartridge Charge (0=fast with soak, 1=fast without soak, 2=slow with soak, 3=slow without soak): ", charge_options)
    volume = get_user_input("Enter Beverage Volume (0=50ml, ..., 15=300ml): ", volume_options)
    flow_rate = get_user_input("Enter Flow Rate (0=30%, ..., 7=100%): ", flow_rate_options)
    purge = get_user_input("Enter Purge (0=slow/short, 1=slow/long, 2=fast/short, 3=fast/long): ", purge_options)

    print(f"temperature: {temperature}")
    print(f"size: {size}")
    print(f"charge: {charge}")
    print(f"volume: {volume}")
    print(f"flow_rate: {flow_rate}")
    print(f"purge: {purge}")

    temperature = reverse_bits(temperature)
    size = reverse_bits(size)
    charge = reverse_bits(charge)
    volume = reverse_bits(volume)
    flow_rate = reverse_bits(flow_rate)
    purge = reverse_bits(purge)
    
    print(f"rev temperature: {temperature}")
    print(f"rev size: {size}")
    print(f"rev charge: {charge}")
    print(f"rev volume: {volume}")
    print(f"rev flow_rate: {flow_rate}")
    print(f"rev purge: {purge}")

    binary_string = purge + flow_rate + volume + charge + size + temperature
    
    print(f"Binary String before padding: {binary_string}")

    # Ensure binary_string is 16 bits long
    total_length = 16

    if len(binary_string) < total_length:
        binary_pad = binary_string.ljust(total_length, '0')
    else:
        binary_pad = binary_string

    print(f"Binary with padding: {binary_pad}")

    # Reverse the binary string
    reversed_binary_pad = binary_pad[::-1]
    print(f"Reversed Binary String: {reversed_binary_pad}")

   # Check if the reversed binary starts with '00' and pad with '0' if necessary
    if binary_pad.endswith('00'):
        pad = '0'
        reversed_binary_pad = reversed_binary_pad[:-1] 
    else:
        pad = ''

    print(f"Reversed Binary String with condition 0 before: {reversed_binary_pad}")

    decimal_value = str(int(reversed_binary_pad, 2))

    decimal_value_with_pad = pad + decimal_value

    print(f"Decimal Value before padding: {decimal_value}")
    print(f"Decimal Value after padding: {decimal_value_with_pad}")

    # Add check digit and format the final string
    check_digit = calculate_check_digit(decimal_value_with_pad)
    decimal_str_with_check = decimal_value_with_pad + str(check_digit)

    # Output and barcode generation

    print(f"Decimal Value with Check Digit: {decimal_str_with_check}")

    # Define the path for saving the barcode image
    img_path = os.path.join(os.getcwd(), f"barcode_{decimal_str_with_check}.png")

    generate_barcode(decimal_str_with_check, img_path)

if __name__ == "__main__":
    main()
