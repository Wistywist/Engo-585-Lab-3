# This is a sample Python script.
import pandas as pd
import os

wifi_data = pd.DataFrame()

locations = ['ENE131', 'ENE329', 'ENC101', 'SG', 'ENC201']
# Press the green button in the gutter to run the script.
if __name__ == '__main__':

    directory = "data"

# iterate through each file in the data directory
    for filename in os.listdir(directory):
        file = os.path.join(directory,filename)
        session_data = pd.DataFrame()

        #open each file and iterate through each line storing to a df
        with open(file) as topo_file:
            for scan, line in enumerate(topo_file):
                dict = eval(line)
                data = pd.DataFrame(dict['wifiAccessPoints'])
                data['scan'] = scan
                session_data = pd.concat([session_data,data])
        session_data['location'] = filename[:-4]

        wifi_data = pd.concat([wifi_data,session_data])
    wifi_data.to_csv("total_data.csv")


    #A) How many access points are visible at each location?
    access_point_count = wifi_data.groupby('location')['macAddress'].nunique()

    #B) To identify Unique mac addresses we simply need to truncate the least significan bit
    # and group them again as in A

    wifi_data['truncated_mac'] = wifi_data['macAddress'].apply(lambda x: x[:-1])
    unique_mac_count = wifi_data.groupby('location')['truncated_mac'].nunique()

    #C) Finding averaege signal strength of each mac Address at each location
    avg_signal_strength = wifi_data.groupby(['macAddress', 'location'])['signalStrength'].agg(['mean', 'std'])
    avg_signal_strength.columns = ['mean_RSSI', 'std_RSSI']

    #   D) Going off the access point count, differentiating between G block locations would be difficult due to the
    #   closeness of signal count, however ENE 131 and 327 are more disticnt in there amounts atleast relative
    #   to the G block building

    # E) identifying location based on signal strength
    # Assuming in D that we have identifiyed our location for ENE block, we will only look at signals for the remaining
    # 3 locations
    # First we need to know how much the signal strength of a mac address varies at a location
    # This is similar to C but instead of grouping by location and mac address we simply need the mac address
    excluded_locations = ['ENE 131', 'ENE 327']
    Gblock_wifi_data = wifi_data[~wifi_data['location'].isin(excluded_locations)]

    # Group by trunucated mac and count the number of unique locations
    mac_location_counts = Gblock_wifi_data.groupby('truncated_mac')['location'].nunique()

    # Filter the dataframe to include only MAC addresses found at all three locations,
    # we dont want to use random one off signal pickups to try and locate our position, so we need to only
    # compare signal strengths at the 3 differen locations
    # these next two lines of code sort the dataframe into just that
    mac_addresses_at_all_locations = mac_location_counts[mac_location_counts == 3].index.tolist()
    Gblock_routers = Gblock_wifi_data[Gblock_wifi_data['truncated_mac'].isin(mac_addresses_at_all_locations)]

    # then we compute the signal strengths overall and by mac address
    Gblock_avg_signal_strength = Gblock_routers.groupby(['location','macAddress'],as_index=False)['signalStrength'].agg(['mean', 'std'])
    Gblock_mac_signal_strength = Gblock_routers.groupby('macAddress',as_index=False)['signalStrength'].agg(['mean', 'std'])

    # now we can simply see if the average values fall within the one sigma of the
    # location based values by taking the differnece between the mean signal strength at a specific location
    # difference from the mean signal strength of the signal across all the locations. The more difference between those
    # values the more likely we are to detected it.
    merged_data = pd.merge(Gblock_mac_signal_strength, Gblock_avg_signal_strength, on=('macAddress'), suffixes=('_overall', '_specific_location'))
    merged_data['difference'] = merged_data['mean_specific_location'] - merged_data['mean_overall']

    # We can simply compare the signal strength difference to a 95% confidence level
    # and simplify our statement to say that if the signal difference at the location
    # is outside the range of std deviation, then we could arguably detected that difference and use it
    # for location
    merged_data['detectable'] = abs(merged_data['std_specific_location']*1.96 ) < abs(merged_data['difference'])
    merged_data.to_csv("Position Detection G Block.csv")


    # To test for detetable signal difference we must take the signal found at a location, and see if the signal difference
    # of other locations is outside of the standard deviation of the isgnal computed at the location.
    # if the signal is outside the standard deviation at a different location then its safe to say we could
    # use that as a way to identify our location, however if the difference is within standard deviations of theat locations
    # we cannot be sure its not just the noise of the signal measurements at that location.
    detectable_signal_strength = pd.DataFrame()
    # Pivot the dataframe to have locations as columns and average signal strengths as values
    pivot_table = merged_data.pivot(index='macAddress', columns='location', values='mean_specific_location')
    pivot_table2 = merged_data.pivot(index='macAddress', columns='location', values='std_specific_location')

    # Iterate through each row of the pivot table

    mac = []
    loc1 = []
    loc2 = []
    difference = []
    stddiff = []
    for index, row in pivot_table.iterrows():
        # Calculate the difference in signal strength between each pair of locations
        for i, location1 in enumerate(pivot_table.columns):
            for j, location2 in enumerate(pivot_table.columns):
                if i < j:
                    diff = row[location1] - row[location2]

                    mac.append(index)
                    loc1.append(location1)
                    loc2.append(location2)
                    difference.append(diff)

                    std_test_location = (diff > abs(pivot_table2[location1][index]*1.96)) and (diff > abs(pivot_table2[location2][index])*1.96)

                    stddiff.append(std_test_location)
                    print(f"Difference in signal strength between {location1} and {location2} for MAC address {index}: {std_test_location}")
    location_check = pd.DataFrame(
        {'macAddress': mac,
         'location1': loc1,
         'location2': loc2,
         'difference': difference,
         'std_test': stddiff
         })

    # This file has a mac address and shows the difference in signal between the two locations listed,
    # a true value indicates that the difference was outside the standard deviations of either locaiton,
    # meaning a position is noticeably different at that point, and a false value means that the difference was
    # within a 95% confidence region and not able to be detected.
    location_check.to_csv('location_check.csv')


    # Finally to test random other user data we need to first import it, which has a different order then our current data.

    directory = "unknown_location"

    # Initialize an empty list to store DataFrames
    dfs = []

    # Iterate through each file in the directory
    for filename in os.listdir(directory):
        if filename.endswith(".csv"):
            # Construct the full path to the CSV file
            filepath = os.path.join(directory, filename)

            # Read the CSV file into a DataFrame
            df = pd.read_csv(filepath)

            # Append the DataFrame to the list
            dfs.append(df)

    # Concatenate all DataFrames in the list into a single DataFrame
    combined_df = pd.concat(dfs, ignore_index=True)
    combined_df.to_csv("test.csv")

    # all we need to compare is the mac addresses and RSSI values
    unknown_location = combined_df[['BSSID', "RSSI"]]
    unknown_location.columns = ['macAddress', 'signalStrength']
    unknown_location['macAddress'] = unknown_location['macAddress'].str.lower()

    # repeating steps performed before, we can group the data by its mac addresses
    unknown_location['truncated_mac'] = unknown_location['macAddress'].apply(lambda x: x[:-1])
    unknown_access_point_count = unknown_location.groupby(['truncated_mac'])['signalStrength'].mean()

    location_pivot_table = pd.pivot_table(wifi_data,columns=['location'],index=['truncated_mac'],values='signalStrength',aggfunc='mean')

    #Upon visual inspection of MAC adrresses in the unknown location it can be seen it lacks the f4:2e mac addresses
    # which eliminates the chance that the location is in ENE block

    merged_unknown = location_pivot_table.merge(unknown_access_point_count, how='inner', left_index=True, right_index=True)
    merged_unknown.to_csv("Unknown_data_assessment.csv")
    # Visual inspection of the pivot table shows that the most mac address matches occur for the South end of G blocks
    # with signal strengths varying heavily but certain low signal strengths matching with low signal strengths on our end.
    # Unfortunately it there are still lots of matches on signals that we did not detect at the south end of the
    # G block that were in the given dataset.
