# Compare csv

Comparison script to compare two csvs and print a summary of differences to the console as well as output the comparison to xlsx.

## Getting Started

* `git clone` repo to preferred location
* open project in preferred IDE
* globally specify tuple of columns within compare.py (examples provided and commented)
* edit parameters within environment variables where `-s` is one input file, `-i` is the other input file and `-o` is the comparison output file:

`-s "dir/path/sas_input_file.csv" 
-i "dir/path/python_input_file.csv" 
-o "dir/path/output_comparison_file.xlsx"`

* run the application and await results.  The longer the wait, the more differences there are.  If there are no differences `Files are equal` will be printed to the console.

### Prerequisites

Listed within requirements.txt. Install via IDE or use `pip install`