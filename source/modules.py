'''
処理の流れ

1 動画を取り込む。
2 動画の各フレームに対して判別をかけて，タグを割り振る。
3 割り振られたタグの一覧データを基に，試合の時間を抜き出して開始・終了フレーム番号のセットに分ける。
4 3をもとに動画を切り出す。
'''
import sys
from itertools import groupby
from operator import itemgetter
import os
import json
import cv2
import ffmpeg
from tqdm import trange
import glob
from PyQt5.QtCore import QMutex, QMutexLocker, QThread, pyqtSignal
import io
from ETA_calc import ETA_calculator
import time

tags_on_video = dict()

class TqdmIO(io.StringIO):

    def write(self):
        self.__init__
        super(TqdmIO,self).write(self)

        

class whole_movie(QThread):

    timeline = {}
    game_times = []

    signal = pyqtSignal(int)
    sig_tqdm = pyqtSignal(str)
    sig_state = pyqtSignal(str)


    def __init__(self,parent=None):
        super(whole_movie, self).__init__(parent)
        self.success_list = []
        self.stopped = False
        self.mutex = QMutex()

    def run(self):
        self.discriminate_video()
        self.write_clip()

    def stop(self):
        with QMutexLocker(self.mutex):
            self.stopped = True

    def initialize(self,src_path):
        #GUIを表示してからインスタンス化ができないので，__init__の役割を別で行う
        self.video_path = src_path
        self.filename = os.path.splitext(os.path.basename(src_path))[0]
        video = cv2.VideoCapture(self.video_path)
        # 幅
        self.W = video.get(cv2.CAP_PROP_FRAME_WIDTH)
        # 高さ
        self.H = video.get(cv2.CAP_PROP_FRAME_HEIGHT)
        # 総フレーム数
        self.num_of_frames =video.get(cv2.CAP_PROP_FRAME_COUNT)
        # FPS
        self.fps = video.get(cv2.CAP_PROP_FPS)
        self.fps_correction_value = int(self.fps/30)
        self.result_margin = 20 * self.fps
        video.release()

    def setOptions(self,force_exec,write_clips,write_whole):
        self.force_exec = force_exec
        self.write_clips = write_clips
        self.write_whole = write_whole

    def discriminate_video(self,**options):
        '''
        動画全体の判別を行います。
        フレーム番号に対して，{start_game,end_game,disconnected}を割り振ります。

        options
        force_exec(int): 1のとき、jsonを無視して捜査処理を実行
        '''
        if self.force_exec == 0:
            if os.path.exists(self.filename+"/game_times.json"):
                with open(self.filename+"/game_times.json") as f:
                    self.game_times = json.load(f)
                return

        self.sig_state.emit("試合時間を探索中")

        sg_frame_list = []
        eg_frame_list = []
        video = cv2.VideoCapture(self.video_path)
        assert(video.isOpened())

        eta_timer = ETA_calculator(time.time(),int(self.num_of_frames))
        for i in trange(int(self.num_of_frames),bar_format = "{l_bar}{r_bar}"):
            #12fps程度に落とす

            if i % self.fps_correction_value == 0:
                ret, frame = video.read()
                if ret:
                    # cv2.imshow("frame",frame)
                    # cv2.waitKey(1)
                    decision = self.__discriminate_frame(frame)
                    # print(decision)
                    if decision == "start_game":
                        # filename = f"{i}_sg.png"
                        # cv2.imwrite(filename,frame)
                        sg_frame_list.append(i)
                    elif decision == "end_game":
                        eg_frame_list.append(i)
            else:
                video.grab()


            
            self.signal.emit(i)
            if i%50 ==1:
                self.sig_tqdm.emit(str(eta_timer.calc(time.time(),i)))
        
        print(sg_frame_list)
        print(eg_frame_list)
        classified_sg_frame_list = self.__find_consecutive_nums(sg_frame_list)
        print(classified_sg_frame_list)
        classified_eg_frame_list = self.__find_consecutive_nums(eg_frame_list)
        print(classified_eg_frame_list)

        sg_time_list = []
        for data in classified_sg_frame_list:
            #2.5秒以上の表示があるとき
            if len(data)>2.5*self.fps/self.fps_correction_value:
                sg_time_list.append(data[0])
        
        eg_time_list = []
        for data in classified_eg_frame_list:
            #1秒以上の表示があるとき
            if len(data)>1*self.fps/self.fps_correction_value:
                eg_time_list.append(data[-1])

        print(sg_time_list)

        print(eg_time_list)

        sg= [[data,"sg"] for data in sg_time_list]
        eg= [[data,"eg"] for data in eg_time_list]
        sgeg = sg + eg
        sgeg.sort()

        for i,data in enumerate(sgeg):
            print(data)
            if i+1 < len(sgeg):
                if data[1]=="sg" and sgeg[i+1][1] =="eg":
                    self.game_times.append({"sg":data[0],"duration":(sgeg[i+1][0]-data[0]) + self.result_margin})


        # for i, sg_time in enumerate(sg_time_list):
        #     for eg_time in eg_time_list:
        #         if sg_time < eg_time:
        #             self.timeline[sg_time] = {"state":"sg","count":i}
        #             self.timeline[eg_time] = {"state":"eg","count":i}
        #             self.game_times.append({"sg":sg_time,"duration":eg_time - sg_time + self.result_margin})
        #             break

        # print(self.timeline)
        print(self.game_times)

        if not os.path.exists(self.filename):
            os.mkdir(self.filename)

        with open (self.filename+"/game_times.json","w") as f:
            json.dump(self.game_times,f)
        
        video.release()
        cv2.destroyAllWindows()

    def write_clip(self,**options):

        self.sig_state.emit("動画を書き出し中")
        # cwd = os.getcwd()
        # bin_path = os.path.join(cwd, 'ffmpeg-4.3.2-2021-02-27-full_build/bin')
        # os.environ['PATH'] += '{};{}'.format(bin_path, os.environ['PATH']) #セミコロン付きでPATHの先頭に追加
        ffmpeg_dir = "./ffmpeg-4.3.2/bin"
        os.environ["PATH"] += os.pathsep + str(ffmpeg_dir)
        print(os.pathsep + str(ffmpeg_dir))
        # print(os.environ["PATH"])
        if not os.path.exists(self.filename):
            os.mkdir(self.filename)
        if self.write_clips:
            print(self.video_path)
            for i, game_time in enumerate(self.game_times):
                stream = ffmpeg.input(self.video_path)

                # 出力
                # stream = ffmpeg.output(stream, f'{self.filename}/{i}.mp4',ss=self.__frame2sec(game_time["sg"]),t=self.__frame2sec(game_time["duration"]))
                stream = ffmpeg.output(stream, f'{self.filename}/{i:04}.mp4',ss=self.__frame2sec(game_time["sg"]),t=self.__frame2sec(game_time["duration"]),c="copy")
                # stream = ffmpeg.output(stream, f'{self.filename}/{i}.mp4',ss=self.__frame2sec(game_time["sg"]),t=self.__frame2sec(game_time["duration"]),vcodec="h264_nvenc",qmin=1,qmax=10)

                # print(self.__frame2sec(game_time["sg"]))
                # print(type(self.__frame2sec(game_time["sg"])))

                # 実行
                ffmpeg.run(stream,overwrite_output=True)
                self.sig_tqdm.emit(f"{i+1}/{len(self.game_times)}")

        if self.write_whole:
            if os.path.exists(self.filename+"/all.mp4"):
                return
            files = glob.glob(self.filename+"/*.mp4")
            with open("tmp.txt", "w") as fp:
                lines = [f"file '{line}'" for line in files] # file 'パス' という形式にする
                fp.write("\n".join(lines))
            # ffmpegで結合（再エンコードなし）
            ffmpeg.input("tmp.txt", f="concat", safe=0).output(self.filename+"/all.mp4", c="copy").run(overwrite_output=True)
        self.sig_tqdm.emit(f"処理完了")


    
    def __discriminate_frame(self,frame_img):
        '''
        1フレームに対する判別を行います。
        self.discriminate_videoから呼ばれます。
        '''

        threshold = 100

        sg_check_pixels_b = [(257,784),(206,1078),(390,1189),(486,777)]
        sg_check_pixels_b=list(map(self.__calc_pixel,sg_check_pixels_b))
        sg_check_pixels_w = [(210,935),(193,962),(182,999)]
        sg_check_pixels_w=list(map(self.__calc_pixel,sg_check_pixels_w))

        eg_check_pixels_b = [(606,790),(444,1692),(229,586),(529,99)]
        eg_check_pixels_b=list(map(self.__calc_pixel,eg_check_pixels_b))
        eg_check_pixels_not_b = [(613,1029),(57,1396),(529,1233)]
        eg_check_pixels_not_b=list(map(self.__calc_pixel,eg_check_pixels_not_b))

        # 二値化(閾値100を超えた画素を255にする。)
        # ret, img_thresh = cv2.threshold(frame_img, threshold, 255, cv2.THRESH_BINARY)
        # print(img_thresh.dtype)
        # print(img_thresh[int(self.H*257/1080),int(self.W*784/1920)])
        #条件とそれに応じた返り値
        #マッチング画面254Frames（初回テスト時）
        # print(type(sg_check_pixels[0]))
        if (self.__is_black_sg(frame_img[sg_check_pixels_b[0]]))\
            and (self.__is_white_sg(frame_img[sg_check_pixels_w[0]]))\
            and (self.__is_black_sg(frame_img[sg_check_pixels_b[1]]))\
            and (self.__is_white_sg(frame_img[sg_check_pixels_w[1]]))\
            and (self.__is_black_sg(frame_img[sg_check_pixels_b[2]]))\
            and (self.__is_black_sg(frame_img[sg_check_pixels_b[3]]))\
            and (self.__is_white_sg(frame_img[sg_check_pixels_w[2]])):
            return "start_game"
        elif (self.__is_black_eg(frame_img[eg_check_pixels_b[0]]))\
            and (self.__is_not_black_eg(frame_img[eg_check_pixels_not_b[0]]))\
            and (self.__is_black_eg(frame_img[eg_check_pixels_b[1]]))\
            and (self.__is_not_black_eg(frame_img[eg_check_pixels_not_b[1]]))\
            and (self.__is_black_eg(frame_img[eg_check_pixels_b[2]]))\
            and (self.__is_black_eg(frame_img[eg_check_pixels_b[3]]))\
            and (self.__is_not_black_eg(frame_img[eg_check_pixels_not_b[2]])):
            return "end_game"

    def __calc_pixel(self,tuple):
        return int(self.H*tuple[0]/1080),int(self.W*tuple[1]/1920)

    def __is_black_sg(self,pixel):
        # if pixel[0] < 7 and pixel[1] < 7 and pixel [2] <7:
        if (pixel<[15,15,15]).all():
            return True
        else:
            return False

    def __is_black_eg(self,pixel):
        # if pixel[0] < 7 and pixel[1] < 7 and pixel [2] <7:
        if (pixel<[55,55,55]).all():
            return True
        else:
            return False

    def __is_not_black_eg(self,pixel):
        if (pixel>[15,15,15]).any():
            return True
        else:
            return False

    

    def __is_white_sg(self,pixel):
        # if pixel[0] > 247 and pixel[1] > 247 and pixel [2] >247:
        if (pixel>[240,240,240]).all():
            return True
        else:
            return False

    def __frame2sec(self,frame):
        return frame/self.fps


    def __find_consecutive_nums(self,data):
        dst = []
        for k, g in groupby(enumerate(data), lambda tuple: self.fps_correction_value*tuple[0]-tuple[1]):
            dst.append(list(map(itemgetter(1), g)))
        return dst
