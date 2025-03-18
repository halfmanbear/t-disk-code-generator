#!/usr/bin/env python3
"""
Barcode Generator Script

This script collects user input parameters, processes them into a binary code,
applies transformations including bit-reversal, padding, conditional adjustments,
and check digit calculation, and generates a corresponding barcode image.
"""

import os
import logging
from PIL import Image, ImageDraw
from typing import Dict

# Setup logging configuration
logging.basicConfig(level=logging.INFO, format='%(message)s')

# Constants for image dimensions and bar widths
IMAGE_HEIGHT = 50
THICK_BAR_WIDTH = 8
THIN_BAR_WIDTH = 4
TOTAL_BINARY_LENGTH = 17

# Barcode pattern mapping for digits 0-9. Each sub-list contains 5 segments:
# 1 indicates a thick bar, 0 indicates a thin bar.
BAR_PATTERNS = [
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

def get_user_input(prompt: str, options: Dict[str, str]) -> str:
    """
    Prompt the user until a valid option is provided.
    
    Args:
        prompt (str): The prompt message.
        options (Dict[str, str]): A dictionary mapping valid input to its binary representation.
        
    Returns:
        str: The corresponding binary string for the selected option.
    """
    while True:
        input_value = input(prompt).strip()
        if input_value in options:
            return options[input_value]
        else:
            logging.info("Invalid input. Please try again.")

def add_bar(draw: ImageDraw.ImageDraw, x: int, y: int, thick: bool) -> int:
    """
    Draw a bar on the image.
    
    Args:
        draw (ImageDraw.ImageDraw): The drawing context.
        x (int): The starting x-coordinate.
        y (int): The starting y-coordinate.
        thick (bool): Whether to draw a thick bar (True) or thin bar (False).
        
    Returns:
        int: The updated x-coordinate after drawing the bar.
    """
    bar_width = THICK_BAR_WIDTH if thick else THIN_BAR_WIDTH
    draw.rectangle([x, y, x + bar_width, y + IMAGE_HEIGHT], fill="black")
    return x + bar_width

def add_space(x: int, thick: bool) -> int:
    """
    Calculate the space to add after a bar.
    
    Args:
        x (int): The current x-coordinate.
        thick (bool): Whether the space is after a thick bar (True) or thin bar (False).
        
    Returns:
        int: The updated x-coordinate after adding the space.
    """
    space_width = THICK_BAR_WIDTH if thick else THIN_BAR_WIDTH
    return x + space_width

def draw_digit_pair(draw: ImageDraw.ImageDraw, first_digit: int, second_digit: int, start_x: int) -> int:
    """
    Draws a pair of digits on the barcode image and returns the new x coordinate.
    
    Args:
        draw (ImageDraw.ImageDraw): The drawing context.
        first_digit (int): The first digit.
        second_digit (int): The second digit (or 0 if not provided).
        start_x (int): The starting x-coordinate.
        
    Returns:
        int: The updated x-coordinate after drawing the digit pair.
    """
    x = start_x
    for j in range(5):
        x = add_bar(draw, x, 0, bool(BAR_PATTERNS[first_digit][j]))
        x = add_space(x, bool(BAR_PATTERNS[second_digit][j]))
    return x

def compute_barcode_width(code: str) -> int:
    """
    Compute the total width required for the barcode image based on the code.
    
    Args:
        code (str): The numeric code as a string.
        
    Returns:
        int: The computed image width.
    """
    width = 0
    # Run-in pattern: two thin bars and two thin spaces
    width += THIN_BAR_WIDTH + THIN_BAR_WIDTH + THIN_BAR_WIDTH + THIN_BAR_WIDTH
    # Barcode for each digit pair
    for i in range(0, len(code), 2):
        first_digit = int(code[i])
        second_digit = int(code[i+1]) if i+1 < len(code) else 0
        for j in range(5):
            width += THICK_BAR_WIDTH if BAR_PATTERNS[first_digit][j] else THIN_BAR_WIDTH
            width += THICK_BAR_WIDTH if BAR_PATTERNS[second_digit][j] else THIN_BAR_WIDTH
    # Run-out pattern: one thick bar, one thin space, one thin bar
    width += THICK_BAR_WIDTH + THIN_BAR_WIDTH + THIN_BAR_WIDTH
    return width

def generate_barcode(code: str, img_path: str) -> None:
    """
    Generate and save a barcode image based on the provided code.
    
    Args:
        code (str): The numeric code to encode in the barcode.
        img_path (str): The file path to save the generated barcode image.
    """
    # Dynamically compute image width based on the code
    image_width = compute_barcode_width(code)
    img = Image.new('1', (image_width, IMAGE_HEIGHT), "white")
    draw = ImageDraw.Draw(img)
    x = 0

    # Draw run-in pattern (start pattern): two thin bars and spaces
    x = add_bar(draw, x, 0, False)
    x = add_space(x, False)
    x = add_bar(draw, x, 0, False)
    x = add_space(x, False)

    # Draw the main barcode from digit pairs
    for i in range(0, len(code), 2):
        first_digit = int(code[i])
        second_digit = int(code[i+1]) if i + 1 < len(code) else 0
        x = draw_digit_pair(draw, first_digit, second_digit, x)

    # Draw run-out pattern (end pattern)
    x = add_bar(draw, x, 0, True)
    x = add_space(x, False)
    x = add_bar(draw, x, 0, False)

    img.save(img_path)
    logging.info(f"Barcode generated and saved as {img_path}")

def calculate_check_digit(code: str) -> int:
    """
    Calculate the check digit for the provided code using a weighted sum algorithm.
    
    Args:
        code (str): The numeric code as a string.
        
    Returns:
        int: The calculated check digit.
    """
    even_sum = sum(int(code[i]) for i in range(0, len(code), 2))
    odd_sum = sum(int(code[i]) for i in range(1, len(code), 2))
    total = (even_sum * 3) + odd_sum
    return (10 - total % 10) % 10

def reverse_bits(binary_value: str) -> str:
    """
    Reverse the order of bits in a binary string.
    
    Args:
        binary_value (str): The binary string to reverse.
        
    Returns:
        str: The reversed binary string.
    """
    return binary_value[::-1]

def process_binary_string(binary_string: str, total_length: int = TOTAL_BINARY_LENGTH) -> str:
    """
    Process the binary string by padding, reversing, conditionally adjusting,
    and converting it to a decimal string.
    
    Args:
        binary_string (str): The binary string to process.
        total_length (int): The desired length of the binary string before processing.
        
    Returns:
        str: The processed decimal string with any necessary padding.
    """
    # Pad the binary string on the right if it's shorter than total_length
    if len(binary_string) < total_length:
        binary_padded = binary_string.ljust(total_length, '0')
    else:
        binary_padded = binary_string
    logging.info(f"Binary string after padding: {binary_padded}")
    
    # Reverse the padded binary string
    reversed_binary = binary_padded[::-1]
    logging.info(f"Reversed binary string: {reversed_binary}")
    
    # Conditional adjustment: if original padded binary ends with '00'
    pad_prefix = ''
    if binary_padded.endswith('00'):
        pad_prefix = '0'
        min_length = max(len(reversed_binary) - 2, 15)
        reversed_binary = reversed_binary[:min_length]
        logging.info(f"Reversed binary string after conditional adjustment: {reversed_binary}")
    
    # Convert binary to decimal string
    decimal_value = str(int(reversed_binary, 2))
    logging.info(f"Decimal value before check digit: {decimal_value}")
    
    return pad_prefix + decimal_value

def main() -> None:
    """
    Main function to collect user input, process the data, generate a barcode,
    and save it as an image.
    """
    # Define options for each parameter
    temperature_options = {"0": "00", "1": "01", "2": "10", "3": "11"}
    size_options = {"0": "0", "1": "1"}
    charge_options = {"0": "00", "1": "01", "2": "10", "3": "11"}
    volume_options = {str(i): format(i, '04b') for i in range(16)}
    flow_rate_options = {str(i): format(i, '03b') for i in range(8)}
    purge_options = {"0": "00", "1": "01", "2": "10", "3": "11"}

    # Collect user inputs
    temperature = get_user_input("Enter Water Temperature (0=cold, 1=warm, 2=83°C, 3=93°C): ", temperature_options)
    size = get_user_input("Enter Size (0=Standard, 1=Large): ", size_options)
    charge = get_user_input("Enter Cartridge Charge (0=fast with soak, 1=fast without soak, 2=slow with soak, 3=slow without soak): ", charge_options)
    volume = get_user_input("Enter Beverage Volume (0=50ml, ..., 15=300ml): ", volume_options)
    flow_rate = get_user_input("Enter Flow Rate (0=30%, ..., 7=100%): ", flow_rate_options)
    purge = get_user_input("Enter Purge (0=slow/short, 1=slow/long, 2=fast/short, 3=fast/long): ", purge_options)

    logging.info("Collected inputs:")
    logging.info(f"Temperature: {temperature}")
    logging.info(f"Size: {size}")
    logging.info(f"Charge: {charge}")
    logging.info(f"Volume: {volume}")
    logging.info(f"Flow Rate: {flow_rate}")
    logging.info(f"Purge: {purge}")

    # Reverse the binary strings for each parameter
    rev_temperature = reverse_bits(temperature)
    rev_size = reverse_bits(size)
    rev_charge = reverse_bits(charge)
    rev_volume = reverse_bits(volume)
    rev_flow_rate = reverse_bits(flow_rate)
    rev_purge = reverse_bits(purge)

    logging.info("Reversed values:")
    logging.info(f"Temperature: {rev_temperature}")
    logging.info(f"Size: {rev_size}")
    logging.info(f"Charge: {rev_charge}")
    logging.info(f"Volume: {rev_volume}")
    logging.info(f"Flow Rate: {rev_flow_rate}")
    logging.info(f"Purge: {rev_purge}")

    # Concatenate reversed binary strings in the required order
    combined_binary = rev_purge + rev_flow_rate + rev_volume + rev_charge + rev_size + rev_temperature
    logging.info(f"Combined binary string before processing: {combined_binary}")

    # Process the binary string to get a decimal value (as string)
    processed_decimal = process_binary_string(combined_binary, TOTAL_BINARY_LENGTH)
    logging.info(f"Processed decimal value (before check digit): {processed_decimal}")

    # Calculate check digit and append it
    check_digit = calculate_check_digit(processed_decimal)
    final_code = processed_decimal + str(check_digit)
    logging.info(f"Final code with check digit: {final_code}")

    # Generate and save the barcode image using dynamic width
    img_path = os.path.join(os.getcwd(), f"barcode_{final_code}.png")
    generate_barcode(final_code, img_path)

if __name__ == "__main__":
    main()
