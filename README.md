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
