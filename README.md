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

<img src="https://latex.codecogs.com/gif.image?\dpi{200}&space;\bg_white&space;AX=Y&space;" title="\bg_white AX=Y " />
<img src="https://latex.codecogs.com/gif.image?\dpi{200}&space;\bg_white&space;X=A^{-1}Y" title="\bg_white X=A^{-1}Y" />

ここにAに揺らぎが生じるとして、εAを入れることで、解となるXにも対応する揺らぎεXが生じます

<img src="https://latex.codecogs.com/gif.image?\dpi{200}&space;\bg_white&space;(A&plus;\varepsilon_A)(X&plus;\varepsilon_X)=Y"/>

Yは消費理性なので値が固定されます。二次項を無視して変形すると、

<img src="https://latex.codecogs.com/gif.image?\dpi{200}&space;\bg_white&space;\varepsilon_X=-A^{-1}\varepsilon_AX=-A^{-1}\varepsilon_AA^{-1}Y"/>

両方に分散を求める場合、Xの分散は以下の式となる

<img src="https://latex.codecogs.com/gif.image?\dpi{200}&space;\bg_white&space;V(\varepsilon_X)=(A^{-1})^{\odot&space;2}\cdot\varepsilon_A\cdot&space;X^{\odot&space;2}" title="\bg_white V(\varepsilon_X)=(A^{-1})^{\odot 2}\cdot\varepsilon_A\cdot X^{\odot 2}" />

