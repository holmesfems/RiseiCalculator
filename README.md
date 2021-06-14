# RiseiCalculator
Calculate AP-Value of materials of Arknights

Usage:
python RiseiCalculator.py

Requarements:
numpy>=1.18.1
sanic>=19.12.2
scipy>=1.4.1
Click>=7.0
pandas

Parameters:
Change Row-491 of RiseiCalculator.py
`rc = RiseiCalculator(minTimes=1000)`
to add or change parameters you want.

Example:
minTimes: The minimize times of valid stage filter
ConvertionDR: the rate of outcome materials, default is 0.18

理性価値表ジェネレーターですわ。
各カテゴリ素材で最適なマップを一つずつ選び、これを基準ステージとします。
基準ステージでは、各素材のドロップ率と理性価値を掛けた合計が、ステージの消費理性と同等の値とします。
加工所の加工では、加工前後の合計理性価値は変動しないものとすれば、これを元に連立方程式を立てることが出来、これを解けば各素材の理性価値が求められます。

<img src="https://latex.codecogs.com/gif.latex?\AX=Y" />
