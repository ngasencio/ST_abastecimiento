
import pandas as pd
import glob
import os

DATA_PATH = r"c:\Users\usuario\Desktop\ST_abastecimiento\ST_abastecimiento\data\data_pac"
patron = os.path.join(DATA_PATH, "PAC*.xls*")
archivos = glob.glob(patron)

print(f"Found files: {archivos}")

for archivo in archivos:
    try:
        print(f"--- Loading {os.path.basename(archivo)} ---")
        # Try loading with default engine first, then xlrd if needed
        try:
            df = pd.read_excel(archivo, nrows=5)
        except Exception as e:
            print(f"Default engine failed: {e}")
            try:
                df = pd.read_excel(archivo, nrows=5, engine='xlrd')
            except Exception as e2:
                print(f"xlrd engine failed: {e2}")
                continue
        
        print(f"Columns: {list(df.columns)}")
        
        # Test detection logic
        posibles = [c for c in df.columns if "OC Asociada" in c or "Orden de Compra" in c]
        print(f"Detected OC columns: {posibles}")
        
    except Exception as e:
        print(f"Error processing {archivo}: {e}")
