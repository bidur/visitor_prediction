import pandas as pd

#trip_code: consecutive trips within a day is assigned same trip_code ( else different trip code)
# It is used for merging trips i.e. merge consecutive tripcount as a single output row 
def assign_trip_code(df_single_ap):
    df_single_ap['trip_code']=None
    df_single_ap = df_single_ap.reset_index(drop=True)
    date_old = 0
    trip_count_old = 0
    trip_code = 0
    
    for idx,row in df_single_ap.iterrows():
        #print(idx)
        cur_trip_count = df_single_ap.iloc[idx].trip_prevs
        cur_date = df_single_ap.iloc[idx].date
        #print(cur_trip_count, trip_count_old, trip_code)
        
        if (trip_count_old ) == cur_trip_count:
            df_single_ap.at[idx,'trip_code'] = str(trip_code)
        elif ( ( (trip_count_old +1 ) == cur_trip_count) ):
            if date_old == cur_date:
                df_single_ap.at[idx,'trip_code'] =  str(trip_code)            
            else:
                trip_code += 1
        else:
            trip_code += 1
            df_single_ap.at[idx,'trip_code'] =  str(trip_code)

        trip_count_old = cur_trip_count
        date_old = cur_date

    return df_single_ap 

def read_input_data(csv_file):
    df = pd.read_csv(csv_file,usecols=['serial','tripid','tripcount','tlm_datagettime','lat','lon'])
    df.rename(columns = {'serial':'ap_id','tlm_datagettime':'timestamp'}, inplace = True)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df=df.sort_values(by=['timestamp'])
    return df


def prepare_trip_summary(df):# summarize each trip
    
    arr_ap_ids = df.ap_id.unique()

    arr_trip_summary = []
    for ap_id in arr_ap_ids:
        df_single_ap = df.query("ap_id=='"+ap_id+"'").copy()
        df_single_ap = df_single_ap.sort_values(by=['timestamp'])
        arr_trips = df_single_ap.tripcount.unique()
        #trip_count = arr_trips[0]
        #trip_count
        ts_prevs = df_single_ap.timestamp.min()
        lat_prevs = df_single_ap.iloc[0].lat
        lon_prevs = df_single_ap.iloc[0].lon

        trip_count_prevs = -9 #  small number (far below real trip_count value) for initialization purpose
        for trip_count in arr_trips:

            # process consicutive trips only e.g. trip_count_prevs = 12 and  trip_count=13
            df_single_trip = df_single_ap.query("tripcount=='"+str(trip_count)+"'").copy()
            df_single_trip = df_single_trip.sort_values(by=['timestamp'])
            max_ts = df_single_trip.timestamp.max()
            min_ts= df_single_trip.timestamp.min()

            stay_time =  min_ts - ts_prevs
            trip_time = (max_ts - min_ts).total_seconds()

            #if (trip_time < 1800): # ignore if the stay_time is less than 30 minutes
            #    continue


            lat_min = df_single_trip.iloc[0].lat
            lon_min = df_single_trip.iloc[0].lon
            lat_max = df_single_trip.iloc[len(df_single_trip)-1].lat 
            lon_max = df_single_trip.iloc[len(df_single_trip)-1].lon

            avg_lat = (lat_prevs + lat_min)/2
            avg_lon = (lon_prevs + lon_min)/2

            lat_prevs = lat_max
            lon_prevs = lon_max

            if ( trip_count_prevs  == trip_count-1):

                arr_trip_summary.append({
                    'ap_id': ap_id,

                    'trip_prevs': trip_count_prevs,
                    'trip_count': trip_count,
                    'ts_prevs': ts_prevs,
                    'ts_min': min_ts,
                    #'ts_max': max_ts,#
                    #'trip_time': trip_time,#
                    'stay_time': stay_time.total_seconds(),
                    'avg_lon_with_prvs': avg_lon,
                    'avg_lat_with_prvs': avg_lat,
                    #'lat_min': lat_min,#
                    #'lon_min': lon_min,#
                    #'lat_max': lat_max,    #        
                    #'lon_max': lon_max #
                    })

            trip_count_prevs = trip_count
            ts_prevs = max_ts

    trip_df =  pd.DataFrame(arr_trip_summary)      
    trip_df['date'] = trip_df['ts_min'].dt.date

    return trip_df


# if multiple consecutive trips in a single day then merge them as single one
def merge_consecutive_trips_in_single_day(trip_df, threshold_in_sec):
    
    arr_ap_ids = trip_df.ap_id.unique()
    arr_trip_merged = []
    for ap_id in arr_ap_ids:
        df_single_ap = trip_df.query("ap_id=='"+ap_id+"'").copy()
        #display(df_single_ap)
        df_single_ap = assign_trip_code(df_single_ap)
        #display(df_single_ap)

        arr_trip_code = df_single_ap.trip_code.unique()

        for trip_code in arr_trip_code:
            df_trip_code = df_single_ap.query("trip_code=='"+str(trip_code)+"'")

            arr_trip_merged.append( {
                        'ap_id': ap_id,
                        'date':df_trip_code.date.min(),
                        'trip_count_prevs': df_trip_code.trip_prevs.min(),
                        'trip_count': df_trip_code.trip_count.max(),
                        'ts_prevs_stop': df_trip_code.ts_prevs.min(),
                        'ts_start': df_trip_code.ts_min.max(), # timnestamp of car starting 
                        'stay_time': df_trip_code.stay_time.sum(),
                        'lon': df_trip_code.avg_lon_with_prvs.mean(), # avg_lon_with_prvs
                        'lat':  df_trip_code.avg_lat_with_prvs.mean(), # avg_lat_with_prvs
                       # 'trip_code': trip_code
                        } )

    df_final =  pd.DataFrame(arr_trip_merged) 
    
    # remove entries with stay_time < threshold_in_sec ( e.g. 1800 seconds)
    df_final = df_final[df_final['stay_time']>=threshold_in_sec]
    #df_final.to_csv(final_csv, index=False) 
    
    return df_final