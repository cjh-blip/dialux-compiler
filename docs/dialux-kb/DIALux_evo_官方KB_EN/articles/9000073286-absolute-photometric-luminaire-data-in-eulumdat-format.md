# Handling of absolute photometry data in EULUMDAT files

> 分类：Solution home / General information / Miscellaneous ｜ 更新：Wed, 27 Apr, 2022 at 11:42 AM
> 来源：https://evo.support-en.dial.de/support/solutions/articles/9000073286-absolute-photometric-luminaire-data-in-eulumdat-format

Summary 

SSL luminaires already have a sizeable market share. In future this will even grow. Unfortunately the SSL technology often does not enable the laboratory to do a relative photometric measurement. Often it is impossible to separate the ‚lamp‛ that means the LED Chip or Cluster from the luminaire or the separation would lead to totally wrong results. One solution to avoid these problems could be the usage of absolute photometry. The documentation of absolute measured photometric data is provided in the IESNA file format IES-LM-63. 
 
This document describes how an EULUMDAT file can be created and interpreted to use absolute measured data instead of relative measured data. This is a common suggestion from Ian
Ashdown, Lighting Analysts and DIAL. 

Motivation 

The lighting industry will be unable to present relative photometric data for specific products respectively clients from the United States and Canada will ask for absolute measured data for SSL luminaires. The widely spread data format EULUMDAT does not offer the possibility to transfer data of absolute photometry. To enable laboratory software and lighting design software to continuously use the well-established EULUMDAT format there are little changes and additions in this format necessary. 
 
Ian Ashdown, Lighting Analysts (AGI32) and DIAL (DIALux) agreed upon a common way to interpret EULUMDAT files that also the handling of absolute photometry is possible. It would be beneficial for the whole lighting industry if luminaire manufacturer, manufacturer of photometric equipment and software manufacturer would act in a common way. 

Implementation 

This document describes how to generate and interpret an EULUMDAT file
containing absolute photometric data. Without any changes to the EULUMDAT file format specification, an EULUMDAT file representing absolute photometry can be interpreted as: 

Item
Designation
Absolute photometry value
Notes

26 
Number n of standard sets of lamps 
1 
1

26a 
Number of lamps 
–n (number of light 
emitters)
2

26b 
Type of lamps 
<Unchanged> 
3

26c
Total luminous flux of lamps (lumens) 
Luminous flux (lm) of luminaire 
4

… 

30
Luminous intensity distribution (cd/klm) 
<Unchanged>
5

Notes
 
- Row 26: There can be only one standard set of lamps for absolute photometry, and the value is fixed at 1. 
- Row 26a: While the number of lamps ‘n’ is meaningless for absolute photometry, it may still be useful to indicate the number of light emitters, such as the number of LEDs. The value is therefore retained, but its sign is negative to indicate absolute photometry.
- Row 26b: Type of lamp is just informative. It could be for example the ILCOS code for a reflector lamp, or the manufacturer’s name for a type of LED.
- Row 26c: In accordance with the principles of absolute photometry, this field reports the measured luminous flux of the luminaire rather than the total manufacturer’s rated lumens of the lamps. An advantage of this interpretation for the luminaire manufacturer is that the reported luminous flux can be measured with for example an integrating sphere rather than a goniophotometer. This makes it possible to measure one luminaire with a goniophotometer to determine its luminous intensity distribution, and then measure multiple identical luminaires to obtain an average total luminous flux value. 
- Row 30: All values are stated in candela per kilolumen (cd/klm). The advantage is that there is no change to the existing format. This interpretation is fully compatible with existing EULUMDAT photometric data files, and also with existing lighting design software programs as long as they do not perform range checking on row 26a. (This is unlikely, as the number of lamps is not required when interpreting the luminous flux distribution of a luminaire.) 

Implementation 

Given that no changes are required to the EULUMDAT file format specification, support for absolute photometry can be provided immediately. Responsibilities
for the various parties include: 
- Photometric Testing Laboratories: Use –n in field 26a to designate absolute photometric data reports. (This is a convention only.)
- Luminaire Manufacturers: Request EULUMDAT files with –n in field 26a for products requiring absolute photometry (primarily for solid-state lighting products, but also for lamps and luminaires with non-removable lamps). 
- Lighting Design Software Manufacturers: Modify future version of their products to indicate EULUMDAT files with absolute photometric data.
