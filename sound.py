import ffmpeg

ffmpeg.input('earth.mp4').filter('hflip').output('out.mp4').run()