# eyes 分层（待绘制）

所有部件在原坐姿下对齐 1122 × 1402 画布；源 PNG 保持 straight alpha，发布时再按 Inox2D 混合要求预乘 Alpha。

目标文件名：
- eye_left_white.png
- eye_left_iris.png
- eye_left_pupil.png
- eye_left_highlight.png
- eye_left_upper_lid.png
- eye_left_lower_lid.png
- eye_left_closed.png
- eye_right_white.png
- eye_right_iris.png
- eye_right_pupil.png
- eye_right_highlight.png
- eye_right_upper_lid.png
- eye_right_lower_lid.png
- eye_right_closed.png

当前只有规格说明，没有实际逐层绘制的部件文件；每一层都应补画原来被盖住的区域。
