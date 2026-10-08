# Guideline for workplaces ASR A3.4

> 分类：Solution home / Calculation / Calculation objects ｜ 更新：Fri, 28 May, 2021 at 11:33 AM
> 来源：https://evo.support-en.dial.de/support/solutions/articles/9000121058-guideline-for-workstation-area-asr-a3-4

In order to use the new calculation surface type for results according to the guideline for workplaces ASR A3.4, three steps are necessary.

1. Placing the area of the workstation
2. Selecting between a surrounding area that fills the room for all workstation areas or a surrounding area as a wall zone for individual workstation areas or groups of workstation areas
3. Documentation of the results

Step 1: Placing a workstation area

To construct an area of the workstation, first switch to the "Calculation objects" mode. There you will find the tool "Work areas" on the left side. As of Evo 5.2, the EN 12464-1 visual task areas and the ASR A3.4 calculation areas are combined in this tool. The tool itself contains a selection catalogue. You can open this via "Select" and choose between the work areas. There you will also find the area of the workstation.

After you have selected the work area in the catalogue, it is selected as an "Active calculation object". Now you can create the calculation area for the workstation in three ways.

Draw rectangular calculation object

Select the action and draw a rectangle in the CAD view at the desired location. The work area is created with a surrounding area that fills the room/ space. By default, the surrounding area does not extend to the walls. There is a wall distance of 0.5m. This value can be adjusted under the "Advanced properties".

Draw polygonal calculation object

Select the action and set several support points in the CAD view. After closing the polygon, the work area is created with the desired shape.

Place calculation object

If you select this action and then click in the CAD view, a 1x1m standard surface is created, which can still be adjusted later via "Scale" or "Edit polygon".

In general, you can subsequently change the shape of work areas according to ASR A3.4 using the "Scale" or "Edit polygon" functions.

Step 2: Select between a room-filling surrounding area for all work areas or a surrounding area as a wall zone for individual work areas or groups of work areas

By default, Evo creates a common surrounding area for workstations. This is always room-filling with deduction of a wall distance. The default value of this distance is 0.5m. If additional workstations are placed in the room, they share the room-filling surrounding area. This is the Evo standard.

However, it is also possible to switch from a surrounding area that fills the room to a surrounding area as a wall zone. To do this, simply select one of the work surfaces and remove the tick from "Surrounding area room-filling". The result is displayed directly in the CAD. Each work surface now has its own surrounding area. 

Evo always creates a new surrounding area for a work surface if it does not intersect another surrounding area. If a work surface intersects a surrounding area of another workspace, this workspace does not get its own surrounding area.

Evo also offers the option of merging surrounding areas. To do this, two surrounding areas must intersect. If they intersect, you must first select both surrounding areas and can then merge them into one integral area with the action "Condense surrounding areas".

Step 3: Documentation of the results

The results for the areas of the workstation can be found in the results overview and the documentation.
