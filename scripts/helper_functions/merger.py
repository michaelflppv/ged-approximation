import os
import glob
import tempfile
import pandas as pd
from openpyxl import load_workbook


def fix_excel_file(file_path):
    """
    Attempts to fix an Excel file by loading it with openpyxl and re-saving it
    to a temporary file.
    Returns the path to the fixed temporary file if successful, or None otherwise.
    """
    try:
        wb = load_workbook(filename=file_path)
        # Create a temporary file name
        temp_fixed = tempfile.mktemp(suffix=".xlsx")
        wb.save(temp_fixed)
        return temp_fixed
    except Exception as e:
        print(f"Failed to fix file {file_path}: {e}")
        return None


def read_and_fix_excel_file(file_path):
    """
    Attempts to read an Excel file. If reading fails, it tries to fix the file
    and read it again.
    Returns the DataFrame if successful, or None if both attempts fail.
    """
    try:
        df = pd.read_excel(file_path, engine="openpyxl")
        return df
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        # Attempt to fix the file
        fixed_file = fix_excel_file(file_path)
        if fixed_file is not None:
            try:
                df = pd.read_excel(fixed_file, engine="openpyxl")
                os.remove(fixed_file)  # Clean up temporary fixed file
                print(f"Fixed file {file_path} and loaded successfully.")
                return df
            except Exception as e2:
                print(f"Error reading fixed file for {file_path}: {e2}")
                os.remove(fixed_file)
        return None


def merge_excel_files(input_dir, output_file):
    """
    Finds all .xlsx files in the input_dir, attempts to fix and read them,
    merges them into a single DataFrame, removes duplicates, and writes the
    result to output_file. If no valid Excel files are found, an exception is raised.
    """
    # Search for .xlsx files in the specified directory
    excel_files = glob.glob(os.path.join(input_dir, '*.xlsx'))

    if not excel_files:
        raise FileNotFoundError(f"No .xlsx files found in directory: {input_dir}")

    dataframes = []
    for file in excel_files:
        df = read_and_fix_excel_file(file)
        if df is not None:
            dataframes.append(df)
        else:
            print(f"Skipping file {file} due to errors.")

    if not dataframes:
        raise ValueError("None of the Excel files could be read or fixed successfully.")

    # Concatenate all DataFrames
    merged_df = pd.concat(dataframes, ignore_index=True)

    # Remove duplicate rows
    merged_df.drop_duplicates(inplace=True)

    # Remove rows where all specified columns equal "N/A"
    # Uncomment the following block to enable this filtering:
    # cols_to_check = ["min_ged", "max_ged", "runtime", "candidates", "matches"]
    # condition = (merged_df[cols_to_check] == "N/A").all(axis=1)
    # merged_df = merged_df[~condition]

    # Ensure the output directory exists; if not, create it
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Write the merged DataFrame to an Excel file
    merged_df.to_excel(output_file, index=False)
    print(f"Merged file saved at: {output_file}")


if __name__ == "__main__":
    # Define the input directory and output file path
    input_directory = r"C:\project_data\results\gedlib\IMDB-BINARY\IPFP"  # Update as needed
    output_file_path = r"C:\project_data\results\gedlib\IMDB-BINARY\IPFP_merged.xlsx"  # Update as needed

    try:
        merge_excel_files(input_directory, output_file_path)
    except Exception as e:
        print(f"An error occurred during merging: {e}")
