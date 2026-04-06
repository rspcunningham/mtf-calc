# USAF 1951 Resolution Test Target Specification

Reference: MIL-STD-150A

## Overview

The 1951 USAF resolution test chart is a standardized optical resolution target consisting of
chromium patterns on a glass substrate (typically 50 mm square). It provides a logarithmic
series of bar patterns used to measure the resolving power of optical systems.

## Structure

- **Groups**: 9 groups (numbered -2 through 7 in the full series; abbreviated versions omit groups 8 and 9)
- **Elements**: 6 elements per group (numbered 1 through 6)
- **Total**: 54 elements in the full series

Each element consists of two sets of three bars (horizontal and vertical) forming a minimal
Ronchi ruling. Bars are separated by spaces equal to the bar width.

## Key Dimensional Rules

- **Bar length-to-width ratio**: 5:1
- **Bar spacing**: space width = bar width (i.e., one line pair = 2× bar width)
- **Frequency step per element**: 2^(1/6) ≈ 1.1225
- **Frequency step per group**: 2× (each group doubles the spatial frequency)

## Black Reference Squares

Even-numbered groups contain a solid black square. The square's edge length equals the
**line length of Element 2** in that group (i.e., 5× the bar width of Element 2).

## Spatial Frequency Formula

```
frequency (lp/mm) = 2^(group + (element - 1) / 6)
```

Bar width (µm) = 1000 / (2 × frequency)

Bar length (µm) = 5 × bar width

## Layout

Groups are arranged in pairs in a compact spiral of three layers:

- **Even-numbered groups**: left side and bottom-right corner
- **Odd-numbered groups**: upper-right corner and right side
- Largest groups occupy the outer layer; progressively smaller pairs spiral inward
- Each even group's black square sits adjacent to the bar patterns

## Line Pairs per Millimeter (lp/mm)

| Element | Group -2 | Group -1 | Group 0 | Group 1 | Group 2 | Group 3 | Group 4 | Group 5 | Group 6 | Group 7 |
|---------|----------|----------|---------|---------|---------|---------|---------|---------|---------|---------|
| 1       | 0.250    | 0.500    | 1.00    | 2.00    | 4.00    | 8.00    | 16.00   | 32.00   | 64.00   | 128.00  |
| 2       | 0.281    | 0.561    | 1.12    | 2.24    | 4.49    | 8.98    | 17.96   | 35.92   | 71.84   | 143.70  |
| 3       | 0.315    | 0.630    | 1.26    | 2.52    | 5.04    | 10.08   | 20.16   | 40.32   | 80.63   | 161.30  |
| 4       | 0.354    | 0.707    | 1.41    | 2.83    | 5.66    | 11.31   | 22.63   | 45.25   | 90.51   | 181.00  |
| 5       | 0.397    | 0.794    | 1.59    | 3.17    | 6.35    | 12.70   | 25.40   | 50.80   | 101.59  | 203.20  |
| 6       | 0.445    | 0.891    | 1.78    | 3.56    | 7.13    | 14.25   | 28.51   | 57.02   | 114.04  | 228.10  |

## Line Width (µm)

| Element | Group -2  | Group -1 | Group 0 | Group 1 | Group 2 | Group 3 | Group 4 | Group 5 | Group 6 | Group 7 |
|---------|-----------|----------|---------|---------|---------|---------|---------|---------|---------|---------|
| 1       | 2000.00   | 1000.00  | 500.00  | 250.00  | 125.00  | 62.50   | 31.25   | 15.63   | 7.81    | 3.91    |
| 2       | 1781.80   | 890.90   | 445.45  | 222.72  | 111.36  | 55.68   | 27.84   | 13.92   | 6.96    | 3.48    |
| 3       | 1587.40   | 793.70   | 396.85  | 198.43  | 99.21   | 49.61   | 24.80   | 12.40   | 6.20    | 3.10    |
| 4       | 1414.21   | 707.11   | 353.55  | 176.78  | 88.39   | 44.19   | 22.10   | 11.05   | 5.52    | 2.76    |
| 5       | 1259.92   | 629.96   | 314.98  | 157.49  | 78.75   | 39.37   | 19.69   | 9.84    | 4.92    | 2.46    |
| 6       | 1122.46   | 561.23   | 280.62  | 140.31  | 70.15   | 35.08   | 17.54   | 8.77    | 4.38    | 2.19    |

## Sources

- [1951 USAF resolution test chart — Wikipedia](https://en.wikipedia.org/wiki/1951_USAF_resolution_test_chart)
- [Applied Image — USAF Targets MIL-STD-150A](https://www.appliedimage.com/product-category/test-targets-and-charts/usaf-targets/)
- [OptoWiki — How to read a USAF 1951 target](https://www.optowiki.info/faq/how-to-read-an-usaf1951-target/)
