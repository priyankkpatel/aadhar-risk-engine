import pandas as pd
import os

BASE_PATH = "data/raw"

def load_folder(folder_name):
    folder_path = os.path.join(BASE_PATH, folder_name)
    all_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(".csv")]

    df_list = []
    for file in all_files:
        df = pd.read_csv(file)
        df_list.append(df)

    return pd.concat(df_list, ignore_index=True)

def load_biometric():
    return load_folder("api_data_aadhar_biometric")

def load_enrolment():
    return load_folder("api_data_aadhar_enrolment")

def load_demographic():
    return load_folder("api_data_aadhar_demographic")
