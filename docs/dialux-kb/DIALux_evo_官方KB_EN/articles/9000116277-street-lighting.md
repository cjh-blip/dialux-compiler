# Revised road lighting , for Evo 6 and above

> 分类：Solution home / Street / Street ｜ 更新：Tue, 26 Apr, 2022 at  1:07 PM
> 来源：https://evo.support-en.dial.de/support/solutions/articles/9000116277-street-lighting

Evo supports the planning of lighting systems for roads in Europe according to:
- EN 13201:2004
- EN 13201:2015
- ROVL 2011

You can start the workspace by clicking on "Street lighting" in the start screen.

The planning mode consists of three main parts:
- the input field on the left (1)
- a list in table form of all street profiles (2)
- a preview of the selected street on the lower edge of the screen (3)

The following five steps are necessary for planning:
- Selection of the standard and description of the street profile
- Configuration of the lighting installation
- Optimisation of the lighting installation
- Export of all results as a *.csv file (optional)
- Documentation of the planning

Step 1 > Selection of the standard and description of the street profile:

When entering the workspace, Evo automatically generates a standard planning case. A road with a width of 7m, 2 lanes and a dry road surface is created. A lighting installation is not yet preselected. The planning standard is initially set to EN 13201:2015. You are in the "Planning" mode in the "Roads" tool.

Selection of the standard
You can change the planning standard under "Active road" in the drop-down menu "Standard". You can choose between EN 13201:2004, EN 13201:2015 and ROVL 2011.

Description of the street profile
To describe the construction parameters of a road, click on the small symbols under "Street profile". Each click on such a symbol adds a new element to the profile.

The following profile elements for describing a street are available for selection:
- Roadway
- Sidewalk
- Bicycle lane
- Lay-bys
- Grass strip
- Emergency lane
- Median

After creating the profile with the profile elements you can now change the order of the profile elements. The arrow indiciates in which the direction the profile element moves.
Each time you make adjustments to the road profile the preview on the lower edge of the screen is updated.

You can add more detailed settings for each of the profile elements. There is always an active profile element in the list. 
Under "Active profile element" you can change the detailed settings. 
For a roadway, for example, you can set the roadway surface and specify the number of lanes.

Selection of the illuminance class

For planning the lighting installation, the illuminance classes for the valuation fields must be specified. An illuminance class contains a set of photometric values including limit values to be complied with. These must be met by the lighting installation.
When you add profile elements, Evo automatically creates valuation fields on the profile elements.
The illuminance class can be selected under "Valuation field" in the "Illuminance class" selection box.

The selection of valid lighting classes may vary from country to country and should therefore be checked in the national standards.
When starting a project, Evo automatically selects a lighting class. This can be changed in the drop-down menu.

Sometimes Evo may not create valuation fields for some profile elements. This is because in the standards no lighting class is required for certain profile elements (e.g. on a grass strip).
Nevertheless by activating "Create new valuation field" you can create a valuation field for such profile elements. After doing this, check the lighting class. You can also delete a valuation field using the action to the right.

Step 2 > Configuration of the lighting installation:

Selection and import of luminaires

To configure the lighting installation, switch to the Luminaire Selection tool in Planning mode. Here you will find a luminaire catalogue. The luminaire catalogue functions similarly to the indoor and outdoor lighting catalogue.
Here, too, you can access the installed/ online luminaire catalogues or LUMsearch.
Using "Import luminaire file" (via icon below the luminaire list), you can also insert common file formats with luminaire data into the catalogue. 

Adding and adjusting a luminaire arrangement
Use the action on the left to add a luminaire arrangement to the currently selected street. Evo creates a luminaire arrangement at the bottom on one side as a default for the active luminaire. Results for the arrangement and the valuation fields are then calculated directly for the street. The preview is updated.

Under Luminaire arrangements you can assign a name to the arrangement and make further detailed settings.
To do this, click on the small triangle to the right of the luminaire. Here you can change the luminous flux, the connected load or the lamp for a luminaire.
If you are planning according to EN 13201:2015, you must enter information on the operating hours of a luminaire arrangement. Again, click on the small triangle on the right. Here you can enter the periods and their associated dimming values for the luminous flux.
Use the "+" to add another time period. Evo calculates the luminous flux and the connected load directly for each period.
This input only appears for the EN 13201:2015 standard, as energy variables of the lighting system are to be calculated here.

Changing the arrangement type
The type of luminaire arrangement can be changed under "Arrangement type". To do this, click on the desired button. The following types are available for selection:
- Arrangement only on bottom side
- Arrangement only on upper side
- Two-sided arrangement
- Two-sided arrangement offset
- Median arrangement (This is only available if the road profile includes a median.)

As a rule Evo always places the luminaires of an arrangement on a roadway. If you do not plan a roadway as a profile element, Evo is oriented to the first and last profile element. You can make further settings to the entire arrangement:
- a rotation of the pole on its own axis
- the number of luminaires per pole
- either the distance of the pole from the roadway or the length of the boom
- a longitudinal displacement of the entire arrangement in relation to the valuation field

Adding luminaire variants
You have the option of calculating several luminaire alternatives per luminaire arrangement. For this purpose, you can add further luminaires as variants. You can make a multiple selection of luminaires in the luminaire catalogue by marking the checkbox of the desired luminaires. You can then add the marked luminaires to the luminaire arrangement via the action "Add luminaires as variants".

After clicking this action, the multiple selection in the luminaire catalogue is reset. Under Luminaire arrangements you will now see the list of luminaire variants.

Step 3 > Optimisation of the lighting system:

Once the street profile and arrangement have been defined, the optimisation can take place. Below the arrangement types you will find the input options for this.

The following parameters can be optimised for the lighting installation :
- Pole distance
- Light centre height
- Boom angle
- Light overhang

Use the checkbox on the right to select and deselect these parameters for optimisation. If the variable is deselected, its associated value is fixed for all calculations. If the size is selected for optimisation, a start value, a target value and an increment can be entered. Evo then creates a calculation scene in the background for each combination. The calculation of these scenes is done via the "Optimise" button. The number of scenes to be calculated depends on the active optimisation parameters, their resolution in the step width and the number of luminaire variants. Evo displays the number of results to be calculated directly. If an optimisation is running, it can also be stopped via the neighbouring button.

The more results have to be calculated, the more time is needed. Evo calculates these scenes in parallel.
The more processor cores available for the calculation, the faster the calculation runs.
There is an upper limit of 30995 results per street profile. If this number is exceeded, luminaire variants must be removed or the optimisation parameters must be set more coarsely.

Display of optimisation results

If no optimisations are active, you can switch to the Result mode. Here you will find an entry in the list on the left for each road profile.
If you select one of the road profiles in the list, the results table is loaded and displayed on the right. Something is only displayed if optimisation has also taken place for the selected road profile.

A result per calculation scene always consists of:
- Information about the luminaire
- Optimisation parameters valid for the result
- Results of all valuation fields
- Advanced photometric values for the luminaire arrangement

If you click on one of the results, the line is highlighted. If you double-click on a result, Evo switches to planning and transfers the data from the result to the associated street profile. The preview is updated.

Step 4 > Export all results (optional):

Evo always saves only one selected result per road. If you have optimised a road profile and want to save all results, export them as a *.csv file. To do this, select your desired street in the "Results" mode under "Alternative". Evo then lists all results in tabular form.

If there are no valid results, the table is empty. 
You can list the non-valid results via the tick "Display insufficient items" and then export them.
In principle, the results that are listed in the table on the right are always exported.

You simply start the export via the action "Export selected result". A file save dialogue for the *.csv file is displayed. Select a storage location and click on Save.

Step 5 > Documentation of the planning:

The last step is the documentation of the planning. This is done in the "Documentation" mode. The tree lists all the roads planned in the project.
There is a "Summary" overview page for each street. There you will find a summary of the luminaire arrangement and the structural parameters of the street.

Below the Summary page you will then find the detailed documentation of the individual valuation fields and their results.
For each valuation field you will receive an overview page with the results and further pages with isolux lines, value graphics and result tables with the photometric results at the grid points.
