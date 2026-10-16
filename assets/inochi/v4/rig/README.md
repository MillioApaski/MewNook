# Inochi Creator 绑定工程（待制作）

计划项目：mewnook_v4_project.inp。最终导出：public/inochi2d/v4/models/MewNook-v4.inx。

基础参数：ParamEyeBlinkLeft / Right，ParamEyeGazeX / Y，ParamMouthOpen，ParamSmile，ParamSleepy，ParamBlush，ParamHeadX / Y，ParamBreath，ParamBodyY，ParamEarLeft / Right，ParamTailSwing。

不要压扁虹膜模拟眨眼；优先用眼睑 ArtMesh、独立口型、尾巴和猫耳网格；保留可重编辑、可重导出的原生工程。


## v4 motion proof-of-concept

`python scripts/upgrade-mewnook-v4.py --source assets/inochi/v4/source/pose_reference.png --input assets/inochi/v4/rig/MewNook-v4-prototype.inx --output assets/inochi/v4/rig/MewNook-v4-motion.inx`

This is an automatically generated **INX** engineering prototype, not an `.inp` native Creator project. Controls: `ParamEyeBlinkLeft`, `ParamEyeBlinkRight`, `ParamMouthOpen`, `ParamSleepy`, `ParamEarLeft`, `ParamEarRight`, `ParamEarLeftTilt`, `ParamEarRightTilt`, `ParamHairLeft`, `ParamHairRight`, `ParamTailDeform`, `ParamSleepyLeft`, `ParamSleepyRight`, `ParamBreath`. The original art needs hidden-region overpainting before visible movements can be considered final.
