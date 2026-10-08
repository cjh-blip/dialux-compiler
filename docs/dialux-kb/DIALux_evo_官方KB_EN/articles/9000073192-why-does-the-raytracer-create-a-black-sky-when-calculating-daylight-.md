# Why is it "outside" dark/black on a raytracing image with daylight?

> 分类：Solution home / Import / Export / Export ｜ 更新：Fri, 9 Apr, 2021 at 11:00 AM
> 来源：https://evo.support-en.dial.de/support/solutions/articles/9000073192-why-does-the-raytracer-create-a-black-sky-when-calculating-daylight-

The calculation of daylight is only carried out inside the building. No statements can be made about the daylight conditions outside. This is also the reason why the sky is displayed in black when using the Raytracer.
The Raytracer uses luminance values for the calculation that are not calculated in the daylight outdoor area.

For the raytracing there is currently only the possibility to avoid such perspectives or to adjust the result afterwards via image processing.
