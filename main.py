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



    print("")