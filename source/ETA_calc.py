class ETA_calculator():
    def __init__(self,time_start,max_index):
        self.time_start = time_start
        self.max_index = max_index

    def calc(self,time_now,index):
        elapsed_time = time_now-self.time_start
        ETA=((self.max_index-index)/index)*elapsed_time
        ETA_str = f"推定残り時間:{int(ETA/60)}分{int(ETA%60)}秒"
        return ETA_str
