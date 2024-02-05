# T-Disk Code Generator

This documentation outlines the barcode generation process for T-Disk beverages, detailing the parameters encoded within the barcode.

## Barcode Parameters

The barcode encodes various parameters for the preparation of the beverage, as outlined below:

- **Water Temperature**
  - `00` - Cold
  - `01` - 88°C
  - `10` - 92°C
  - `11` - 94°C

- **T-Disk Size**
  - `0` - Regular T-Disk
  - `1` - Large T-Disk

- **Pre Brewing**
  - `00` - Fast charge with soak
  - `01` - Fast without soak
  - `10` - Slow charge with soak
  - `11` - Slow charge without soak

- **Volume**
  - `0000` - 50 ml
  - `0001` - 60 ml
  - ...
  - `1111` - 300 ml

- **Flow Rate**
  - `000` - 30%
  - `001` - 40%
  - ...
  - `111` - 100%

- **Purge**
  - `00` - Slow/short
  - `01` - Slow/long
  - `10` - Fast/short
  - `11` - Fast/long

- **Misc/Padding**
  - `00` - Padding
  - `01` - (Reserved)
  - `10` - Costa Americano
  - `11` - Starbucks / Maxwell

## Example Code Breakdown

### Vanilla Latte (Coffee) - Code: `061780`

1. **Binary Conversion**
   - Original Code: `061780`
   - Remove Check Bit: `06178`
   - Convert to Binary: `1100000100010` (13 bits)
   - Reverse: `0100010000011`
   - Padded to 17 bits: `00000100010000011`

2. **Parameter Breakdown**
   - Temperature: `11` (93°C)
   - Size: `0` (Standard)
   - Charge: `00` (Fast with soak)
   - Volume: `0010` (70ml)
   - Flow: `001` (70%)
   - Purge: `00` (Slow/short)
   - Misc: `0` (Padding)

3. **Decimal Values**
   - Before Padding: `11000001000100`
   - After Padding: `00011000001000100`
   - Trimmed: `0001100000100010`
   - Decimal: `6178`
   - With Pad: `06178`
   - With Check Bit: `061780`

### Twinings Earl Grey - Code: `032711`


