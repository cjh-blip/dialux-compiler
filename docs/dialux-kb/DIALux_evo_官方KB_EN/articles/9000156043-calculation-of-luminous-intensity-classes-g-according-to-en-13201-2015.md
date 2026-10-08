# Calculation of the luminous intensity

> 分类：Solution home / Calculation / Calculation method ｜ 更新：Fri, 11 Jun, 2021 at 11:32 AM
> 来源：https://evo.support-en.dial.de/support/solutions/articles/9000156043-calculation-of-luminous-intensity-classes-g-according-to-en-13201-2015

For the calculation of luminous intensity classes in accordance with EN 13201:2015, the luminous intensities in [cd/klm] relative to luminaire luminous flux shall be used.

Amendment to EN 13201:2003!

In LDT photometry files, however, it is usual to specify luminous intensity values in [cd/klm] relative to the luminous flux of the lamp. In the output of luminous intensity tables, Evo always displays the luminous intensities listed in the photometric file. Unless it is an absolute photometry with a negative indicator. Here, evo displays the luminous intensity table directly in [cd]. 

However, since EN 13201:2015 requires luminous intensities to be expressed in [cd/klm] in relation to luminaire luminous flux, Evo must first convert the luminous intensities from the photometric file:

Case studies:
- Relative Photometry
Lamp luminous flux: 13846 lm
Luminaire luminous flux: 9000 lm
- Light output ratio: 9000 lm / 13846 lm = 0.65 => 65% 
 
- For example, the luminous intensity table shows a maximum value (range 70°-80°) of 356 cd/klm. However, this value refers to the 13846 lm lamp luminous flux. However, due to the requirement in EN 13201:2015 to refer this luminous intensity value to luminaire luminous flux, we have to carry out the following calculation:
 
- Lamp luminous flux: 13846 lm * 0.65 = 9000 lm
- Luminous intensity value (c,y): 356 cd/klm / 0.65 = 548 cd/klm (356cd/klm is in the photometry file, 548 cd/klm is to be used according to EN 13201:2015 for the light intensity class)

This result leads to a luminous intensity class of G*3.
If we would not carry out the conversion of the luminous intensity values here, the Integral IdOmega over all luminous intensities would no longer give 9000 lm luminaire luminous flux. The photometry would therefore no longer be correct! 

- Absolute Photometry
Lamp luminous flux: 9000 lm
Luminaire luminous flux: 9000 lm
- Light output ratio: 9000 lm / 9000 lm = 1.00 => 100% 
 
- From the luminous intensity table, for example, a maximum value (range 70°-80°) of 548 cd/klm can be read. As with relative photometry, this value refers to the 9000 lm lamp luminous flux. However, due to the requirement in EN 13201:2015 to refer this luminous intensity value to luminaire luminous flux, we have to carry out the following calculation:
 
- Lamp luminous flux: 9000 lm * 1 = 9000 lm
- Luminaire luminous flux (c,y): 548 cd/klm / 1.00 = 548 cd/klm (548cd/klm is in the photometry file, 548 cd/klm is also to be used according to EN 13201:2015 for the light intensity class)

This result also leads to a luminous intensity class of G*3.
Since luminaire luminous flux and lamp luminous flux are the same in an absolute photometric file, the values in [cd/klm] can be read directly from the table. Since lamp luminous flux and luminaire luminous flux are the same, the luminous intensity values in [cd/klm] are logically also those relating to luminaire luminous flux. The requirements of EN 13201:2015 have been met.
