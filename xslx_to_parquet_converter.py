import os
import pandas as pd

directory = "results/analysis/HED/AIDS"  # Change to your actual path

for filename in os.listdir(directory):
    file_path = os.path.join(directory, filename)

    if filename.endswith(".xlsx"):
        try:
            # Check if the file is actually an Excel file
            with open(file_path, "rb") as f:
                first_bytes = f.read(2)

            if first_bytes == b'PK':  # 'PK' signature → it's a real .xlsx file
                engine = "openpyxl"
                df = pd.read_excel(file_path, sheet_name=None, engine=engine)  # Load all sheets

            elif first_bytes == b'\xEF\xBB' or first_bytes.isascii():  # Likely a CSV
                print(f"Warning: {filename} is a CSV, not a real Excel file. Converting it as CSV.")
                df = {"Sheet1": pd.read_csv(file_path)}  # Convert single sheet CSV

            elif first_bytes.startswith(b'{') or first_bytes.startswith(b'['):  # Likely a JSON
                print(f"Warning: {filename} is a JSON, not a real Excel file. Converting it as JSON.")
                df = {"Sheet1": pd.read_json(file_path)}

            else:
                print(f"Skipping {filename}: Unknown format.")
                continue

            # Convert each sheet to Parquet
            for sheet_name, sheet_df in df.items():
                parquet_filename = f"{filename.replace('.xlsx', '')}_{sheet_name}.parquet"
                parquet_path = os.path.join(directory, parquet_filename)

                sheet_df.to_parquet(parquet_path, engine="pyarrow", compression="snappy")

            print(f"Converted {filename} to {parquet_filename}")

        except Exception as e:
            print(f"Error processing {filename}: {e}")
            continue

print("Conversion completed.")
