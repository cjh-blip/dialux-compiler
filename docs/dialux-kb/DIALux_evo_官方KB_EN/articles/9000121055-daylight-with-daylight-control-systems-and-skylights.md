# Daylight with daylight control systems and skylights

> 分类：Solution home / Light / Daylight ｜ 更新：Thu, 20 May, 2021 at  1:53 PM
> 来源：https://evo.support-en.dial.de/support/solutions/articles/9000121055-daylight-with-daylight-control-systems-and-skylights

Since DIALux evo 6, the designer can include real daylight control systems, skylights and façade elements in his daylight calculation. In the photo-realistic visualisation, sunlight incidence and shadows can be seen at a glance and evaluated.

These include vertical louvre blinds and textile blinds, skylights, foils and prismatic systems. Several light-directing elements can be placed and configured on windows in layers. Depending on the date, time, orientation of the building and sky model, the daylight quotient and illuminance inside the building are determined.

A completely new tool for daylight control systems is available to you for configuring the products. Here you can set the site of the lighting installation, the motion /status of movement of window fittings, control strategies and the angle of inclination. Once configured, systems can be easily transferred to other windows. 

In addition to rectangular skylights, DIALux now simulates photometrically measured domes, skylights and continuous rooflights.

Electronic catalogues of reputable manufacturers of sun shading and daylight control systems are available for product selection. The catalogue selection can be filtered specifically for these new suppliers of daylight-relevant products. Alternatively, you can import product data via the open ODLS (Open Daylight System) format or DIALux's own DDLS format. They contain images and product descriptions, as well as all technical data required for the lighting calculation. All calculation results are available in the results overview and in the project documentation. In addition, there is documentation of the daylight situation and detailed product descriptions. The light-directing properties can be seen at a glance with the help of the new hemispherical transmission diagram.

General

Since version evo 6, the effect of skylights and façade elements can be simulated and taken into account when calculating daylight scenes. Real, physically measured products are used for which separate catalogues are available. DIALux evo uses a new calculation method that was developed in cooperation with the Fraunhofer Institute for Building Physics. Unlike other light simulations, the daylight control systems are not calculated using ray tracing. Instead, the photometric properties of the products are physically measured and their effect of the daylight situation and the effect of the products on each other are determined algorithmically. This enables a fast and accurate calculation of the complete scenes.

Product types

- Louvre blinds 

Louvre blinds are movable or rigid daylight control systems consisting of horizontal or vertical louvres. There are systems that are suitable for use inside the building, for the external façade or for both. They are mostly used to block direct sunlight and steer indirect daylight into the interior of the building. They are manually controlled or automatically track the sun.

- Blinds 

Blinds are systems for darkening or serve as sun protection. They are mostly used inside buildings. However, there are also systems for outdoor use.

- Foils 

Foils are placed directly on the glass pane. They serve as UV protection, privacy protection or have light-directing properties with microstructures.

- Skylights 

Light domes or continuous rooflights can be used as skylights in DIALux. Light domes have fixed dimensions. Continuous rooflights can be scaled within predefined limits. Skylights cut openings in the building envelope like windows. They are automatically adjusted to the roof pitch and cut vertically into the roof surface. Skylights can be rotated by the user. The user must ensure that no further openings are created at the transition between the skylight and the roof surface.

- Material for roof windows 
 
Unlike windows, no new layers of solar shading or daylight deflection systems can be added to skylights in DIALux. However, the standard DIALux evo skylights can be fitted with additional materials just like windows. This allows special shapes of skylights to be constructed, or skylights in old projects to be retrofitted with light-directing properties.

- Prismatic systems 

Light-directing glasses are static systems, i.e. non-adjustable systems, which are used in the space between the panes of glass or directly as panes. Through specially shaped profiles or structures, they direct daylight specifically into the interior of the building.

- Self-rotating prismatic systems 

This special form of light-deflecting glass uses a mirrored micro-louvre structure that is rotated depending on the building orientation and roof pitch. The direct incidence of sunlight is minimised in the process. This alignment is carried out once during the manufacture of the light-deflecting glass. It is therefore also a non-dynamic system. The optimal alignment of the self-rotating light control glass is automatically carried out by DIALux. Subsequent rotation by the user is not possible.

Limitations

The calculation with daylight control systems is subject to some limitations that the planner must take into account and to which we would like to draw your attention here:

- Calculation time 

When calculating with daylight and daylight control systems, the building apertures are divided into small areas. The subdivision depends on the situation and is dependent on the size, the construction and the system used. A separate light intensity distribution curve is calculated for each partial area. Many large window areas with many daylight control systems thus lead to a longer calculation time.

- Outdoor areas 

The calculation is only carried out inside the building, no statements can be made about the daylight conditions outside. This is also the reason why the sky is shown in black when using the ray tracer.
The ray tracer uses luminance values for the calculation that are not calculated in the daylight outdoor space.

- Inner courtyards 

Currently, DIALux evo does not recognise windows that are oriented towards an inner courtyard as daylight-relevant. The daylight from inner courtyards can therefore not be calculated.

- Visualization 

Skylights are represented by a highly simplified geometry. The angles of attack of louvres are not shown in the visualisation, but are calculated correctly in terms of lighting technology.

- Standardized skies 

The calculation is based on the standardised sky models as described in CIE 110-1994 "Spatial Distribution of Daylight - Luminance distributions of various reference skies" of 1994: Overcast Sky, Averaged Sky and Clear Sky. A luminance is assigned to each point of the sky. The luminance depends on the sun elevation, the sun azimuth, the sky point elevation and the sky point azimuth. The calculation of luminous values with the help of these standardised sky models may deviate from the actual values on site. Please note that due to the newly introduced soiling factors for window panes, there may be small differences in the calculation between DIALux evo 6 (or newer) and older versions.

- Quantity of sun shade and daylight control systems 

Due to the calculation algorithms used, façade elements can only be calculated up to a thickness of 0.4m. DIALux evo calculates up to a maximum of four layers of solar shading and daylight control systems.

Working with sun protection and daylight control systems
 A prerequisite for planning with sun protection and daylight control systems are building apertures such as windows and roof windows, as well as at least one light scene with active daylight calculation. You activate the daylight calculation by selecting a sky model in the corresponding light scene.

You receive product data in the form of ODLS files directly from the manufacturer of the daylight control systems. The action "Load daylighting system file" opens the corresponding file dialogue. After loading an ODLS file, you would still have to assign a product type to the product (louvre blind, blind, foil, prismatic system, material for roof window). Alternatively, you can install the electronic catalogues. The catalogues offer a detailed product presentation and a convenient product search.

Tools

In the "Construction" mode you will find the tool "Façade elements". Under "Active façade element" you will find a product image, the name of the selected façade element, and a logo of the manufacturer. Via "Select" you can access the last used façade elements, your personal favourites or the installed catalogues. You will find the catalogues or the source where you can obtain them in the "Manufacturer" mode.

- Placing façade elements
To place a façade element, first select a window in the CAD. With the "Add façade system" action 

you add a new layer to the selected window. You will find it again under "Layer configuration". Please check the position of the façade element (inside or outside) and the distance to the already existing glass pane.

You can change the order directly with the mouse or by using the two control arrows. You can configure up to four layers per window.
 
- Layer properties 
Here you can change the properties of the individual layers, for example position of a textile blind or the angle of a louvre blind system. Not all products have position status, such as foils. The position status can be entered as a percentage value in relation to the entire window area, as an absolute value in metres, or using the slider.

- Calculation 

As with artificial light and the previous daylight calculation, the calculation is carried out via the "Start calculation" or "Continue calculation" buttons.

- Documentation

In the documentation you will find two separate outputs for daylight control systems. 

- Product data sheets 

The product data sheets for sun protection and daylight control systems show a hemispherical transmission diagram in addition to pictures, a descriptive text and the dimensions of the product. This shows the transmittance of the product in percent depending on the incident light. For configurable products, a separate diagram is displayed for each measured data set.

- Daylight systems 
The "Daylight systems" output shows the position and layer configuration of the individual daylight control systems. In the settings you can set the types of daylight in the output.
