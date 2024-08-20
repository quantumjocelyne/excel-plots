import matplotlib.pyplot as plt
import glob
import os
from fuzzywuzzy import fuzz, process
import warnings
import pandas as pd

warnings.filterwarnings("ignore", module="fuzzywuzzy")

def find_header_row(df, expected_header_names, unwanted_header_elements):
    # Iterate through rows and search for a row which closely matches the expected_header_names
    for i, row in enumerate(df.iterrows()):
        row_text = " ".join(str(cell) for cell in row[1])

        # Check if any unwanted_header_element exists in the file's row_text
        if any(unwanted in row_text for unwanted in unwanted_header_elements):
            continue

        # Use fuzzy matching to compare the row text to expected header names
        best_match = find_best_match(row_text, expected_header_names)
        ratio = fuzz.token_set_ratio(row_text.lower(), best_match.lower())
        if ratio >= 80:  # Adjust the threshold (if needed)
            return i
    return None

def find_best_match(needle, haystack):
    best_match, _ = process.extractOne(needle, haystack)
    return best_match


def clean_and_process_excel_files(files, expected_header_names, unwanted_header_elements, dpi=500, timestamp_count=10,  temp_range=(5, 30), relH_range=(20, 80), combined_plot=True):

    global fig
    num_files = len(files)

    if combined_plot:
        num_cols = 2
        num_rows = (num_files + 1) // num_cols

        # Dynamic figure height: based on the number of files uploaded
        single_height = 5  # Optimal height of a single plot
        fig_height = single_height * num_rows
        fig, axs = plt.subplots(num_rows, num_cols, figsize=(15, fig_height))
        plt.subplots_adjust(hspace=0.8)  # Adjust as needed (the subplots may have different time stamps each)
    else:
        axs = None

    for i, file in enumerate(files):
        try:
            print(f"Processing file: {file}")
            df = pd.read_excel(file, header=None)
            header_row = find_header_row(df, expected_header_names, unwanted_header_elements)
            print(f"Header row: {df.iloc[header_row].values}")
            if header_row is not None:
                df = pd.read_excel(file, skiprows=header_row)
            else:
                raise Exception("Header row not found")


            if combined_plot:
                if num_files == 2:  # Prevent deformed plots: if there are only two files (on the combined plot), axs is 1D
                    ax_left = axs[i]

                else:
                    row = i //num_cols
                    col = i % num_cols
                    ax_left = axs[row, col]
            else:
                fig, ax_left = plt.subplots(figsize=(8, 6))


            ax_right = ax_left.twinx()

            # Dynamically get the temperature and relative humidity headers
            temp_headers = [col for col in df.columns if "Temperatur" in str(col) or "Lufttemperatur" in str(col)]
            rh_headers = [col for col in df.columns if "Feuchtigkeit" in str(col) or "Luftfeuchte" in str(col)]

            if temp_headers and rh_headers:
                temp_header = temp_headers[0]
                rh_header = rh_headers[0]

                ax_left.plot(df["Datum/Uhrzeit"], df[temp_header], color='red', linewidth=0.6)
                ax_right.plot(df["Datum/Uhrzeit"], df[rh_header], color='blue', linewidth=0.6)

                # Display the timestamps on the x-axis (with default valie that can be customised later)
                num_ticks = 10
                ticks = df["Datum/Uhrzeit"].iloc[::len(df) // timestamp_count].values
                ax_left.set_xticks(ticks)
                ax_left.set_xticklabels(ticks, rotation=65, ha='right')   # Adjust rotation angle if x-axis labels do not risk to overlap with the plot below


                ax_left.set_ylabel('Temperature [°C]')
                ax_right.set_ylabel('Relative Humidity [%rF]')

                ax_left.set_ylim(temp_range)
                ax_right.set_ylim(relH_range)

                ax_left.tick_params(axis='y', colors='red')
                ax_right.tick_params(axis='y', colors='blue')

                ax_left.spines['right'].set_visible(False)
                ax_left.spines['left'].set_color('red')
                ax_right.spines['left'].set_visible(False)
                ax_right.spines['right'].set_color('blue')

                ax_left.yaxis.labelpad = 15
                ax_right.yaxis.labelpad = 15

                ax_left.spines['top'].set_visible(False)
                ax_left.spines['bottom'].set_visible(True)
                ax_right.spines['top'].set_visible(False)
                ax_right.spines['bottom'].set_visible(True)

                ax_left.xaxis.set_ticks_position('bottom')
                ax_right.xaxis.set_ticks_position('bottom')

                ax_left.tick_params(axis='x', bottom=True)
                ax_right.tick_params(axis='x', bottom=True)

                file_name = os.path.splitext(os.path.basename(file.split(os.sep)[-1]))[0]

                ax_left.set_title(file_name)

                if not combined_plot:
                    save_path_individual = os.path.join("static", f"{file_name}_plot.png")
                    plt.tight_layout()
                    plt.savefig(save_path_individual, dpi=dpi, bbox_inches='tight')
                    print(f"Figure saved to {save_path_individual}")


            else:
                print(f"Temperature and/or relative humidity headers not found in {file}.")

        except Exception as e:
            print(f"Error processing file : {e}")

    if combined_plot:
        if num_files % 2 != 0:
            fig.delaxes(axs[-1, -1])

        save_path_combined = os.path.join("static", "Plots.png")
        plt.savefig(save_path_combined, dpi=dpi, bbox_inches='tight')
        print(f"Combined figure saved to {save_path_combined}")


# Define the expected header names to match
expected_header_names = ["Datum/Uhrzeit", "Temperatur[°C]", "rel.Luftfeuchte[%rF]", "Lufttemperatur[°C]", "%Feuchtigkeit[%rF]"]
# Define the unwanted header elements to ignore
unwanted_header_elements = ["Temperatur [°C]", "rel.Luftfeuchte [%rF]", "Lufttemperatur [°C]", "%Feuchtigkeit [%rF]"]

# Call if run locally:
# clean_and_process_excel_files("your file's path here", expected_header_names, unwanted_header_elements, combined_plot=False)