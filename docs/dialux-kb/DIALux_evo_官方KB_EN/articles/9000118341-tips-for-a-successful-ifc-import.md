# Requirements for a good IFC import

> 分类：Solution home / Import / Export / Import ｜ 更新：Fri, 6 Jun, 2025 at  1:27 PM
> 来源：https://evo.support-en.dial.de/support/solutions/articles/9000118341-tips-for-a-successful-ifc-import

This article describes how the IFC import works in DIALux and also provides tips on how IFC building models should be structured to ensure a successful import into DIALux.
 
The IFC file format offers some freedom in the description of building architecture, building environment and technical building equipment. This degree of freedom means that errors, misinterpretations or inaccuracies can creep in. Basically, poor quality in IFC models poses challenges for any programme with an IFC interface and makes smooth planning in an open BIM context more difficult.
 
DIALux evo with its IFC interface is also affected and aims to import models as completely as possible. This will not succeed for all models. Some are simply too large and exceed the computer's resources or basic rules have been violated when designing the model. The overall data quality is very inhomogeneous.

Documentation on the IFC data model and its IFC objects can be found here: IFC Specifications

Table of contents
- 1- Minimum requirements of an IFC model- Requirements for a building model
- Requirements for other structures or constructions

- 2 - Settings for the IFC import- Comparison of new and old method

- 3 - How does DIALux handle insertion points?
- 4 - How do I load Autodesk Revit models into DIALux? - Dealing with the 'Building Storey' checkbox

- 5 - What characterises high model quality?- Windows (doors) with wall openings
- Materials and colours
- Correct use of IFC types
- Which IFC types are supported?
- Which IFC objects are not supported or ignored?
- Which IFC versions are supported?
- Helpful export settings in CAD programmes

- 6 - What to do if IFC models are too cumbersome for the computer and/or DIALux?
- 7 - FAQ

1- Minimum requirements of an IFC model

When importing IFC models, DIALux distinguishes between a building in the narrower sense and other structures or constructions. The minimum requirements for the content of the IFC files, i.e. the IFC models, are described below for both cases.

Requirements for a building model

If the IFC model describes a building structure, the following IFC objects must be summarised in a single IFC file. Building structure refers to an application from building construction. This means a model that is made up of buildings, storeys and spaces.

DIALux requires the cubature including room layout in an IFC file to interpret the building. They should belong together:

- Exterior walls
- Storey ceilings and floors,
- Partition walls (to separate rooms),
- Windows and doors,
- Roof constructions with skylights
- and new from DIALux evo 13, spaces

If these objects are available together in an IFC file, DIALux will interpret the building model and reconstruct it in its own scene. This is necessary because DIALux evo 13 can currently only load one IFC file. 

We are working on being able to load several IFC files. It is often the case that different aspects of a building model are split across several IFC files. This is intentional in the open BIM workflow. However, IFC tools can usually merge several IFC files into one and save them again (merge). Such a merge is currently still required.

Requirements for other structures or constructions

If the IFC model is not a building in the narrower sense, all IFC components of this construction or building should be structurally assigned to the IFC site. This can usually be configured when exporting in the authoring software.

Such IFC models are processed slightly differently internally by DIALux. It is not necessary to use the construction logic of buildings and storeys for such models. This option is a kind of ‘joker’. This means that IFC models with any content can be imported into DIALux. 

We have seen IFC models containing, for example, roads, bridges, tunnels, steel structures or simply an exterior design. In such cases, the components should be assigned to the site.

2 - Settings for the IFC import

The IFC import takes place in three steps:
- The first step is to select which IFC content DIALux should import. Initially, everything is preselected. If required, larger models can be reduced to a subset here.

- In the second step, you select how DIALux should process the IFC objects during import. Here DIALux distinguishes between a new method (from DIALux evo 13) and an older method. The difference is explained below.

- In addition, reflectance factors can be adjusted in the second step. DIALux determines reflectance directly from the material information in the IFC model. For normative assessments, it may be useful to overwrite the reflectance values with the values in general settings during import. These values can be adjusted under Settings > General settings > Project > Reflection factor.

- After clicking Finish, DIALux imports the IFC model into its own data structures. If successful, you can then see the result in the CAD view. If there are any problems with the IFC model, DIALux notes all issues in a text file, which can be saved for further problem analysis at the bottom right.

Comparison of new and old method

In the second step of the IFC import, you select how DIALux should process the IFC objects. A programme such as DIALux requires a software component called a solid modeler. A solid modeller can, for example, merge several individual 3D solids into a new solid or subtract two 3D solids from each other to determine the difference solid. In DIALux, for example, there would otherwise be no holes in the walls in which windows or doors are inserted. Solid modeller operations are time-consuming on the one hand. On the other hand, numerical inaccuracies can occur during the operations, which manifest themselves in the form of instabilities during import.
 
This is usually the reason why IFC models are incomplete or cannot be loaded into DIALux.

- The strategy of the new method is to minimise the number of Solid Modeler operations during the import. A smaller subset of the building model is processed by the solid modeller. This in turn saves time and leads to greater stability. In our tests, we were able to save up to 90% of the import time (depending on the IFC model). Models that could not be imported before can be processed easily and with fewer errors using the new method. The finer the details and the more complex the IFC model, the more suitable this method is.

Minimising Solid Modeler operations leads to the following side effects. DIALux marks hidden surfaces in its data model as so-called connection surfaces. Connecting surfaces are, for example, places where walls, storey ceilings, storey floors or other walls touch. During light visualisation, DIALux ensures that light is limited at these connecting surfaces so that it does not shine through on the other side of these surfaces.

If you opt for the new method, these connecting surfaces are no longer determined in the entire model. As a result, even if IFC objects touch each other cleanly and are constructed without gaps, light can still shine through. In addition, shadows can occur in corners during light visualisation. This influence on the calculation results of calculation surfaces is rather small. The light visualisation no longer looks as good.

- With the old method, the complete building model is always processed by the Solid Modeller and all connecting surfaces are determined. This means that the import usually takes longer and also causes the instabilities already mentioned. Due to all the marked connecting surfaces, you get a more beautiful light visualisation here.

- Basically, a deal is being struck here:
- if the new method is chosen, you opt for a less attractive light visualisation in favour of a faster and more stable IFC import.
- If the old method is chosen, you opt for a more attractive light visualisation at the expense of a slower and less stable IFC import.

The choice between the new and old method is available from DIALux evo 13 and there are no disadvantages in terms of compatibility with the new method in future versions. We are working on a solution to combine the best of both methods in a later version. This offer is intended as an interim step and will change in the future.

3 - How does DIALux handle insertion points?

IFC models always have an insertion point (coordinate system). An insertion point is, for example, the site coordinate system. DIALux adopts the exact insertion point from the site of the IFC model for its own scene. This means that the exported IFC luminaire model can later be superimposed with the IFC building model at this point.

- There is one restriction here:

It is important for DIALux that its own coordinate systems are positioned as close as possible to the building. If the insertion point in the IFC model and the positions of all IFC components are very far apart, rounding inaccuracies will occur in the results and light visualisation. In this situation, the coordinates of all components are very large. 
Computers work internally with floating point numbers. The larger the number before the decimal point, the fewer digits after the decimal point. The more digits after the decimal point, the more accurate the calculation results. We have seen models where the coordinates are sometimes greater than 10,000 or 100,000.

DIALux attempts to move its own insertion point closer to the building during import. If necessary, this is done automatically when importing the IFC model. During this process, however, DIALux remembers the original insertion point from the IFC model. This means that the coordinates of the exported IFC luminaire model are always exported to the original insertion point of the IFC model. This ensures that the models can be positioned exactly on top of each other again.

- If the attempt did not work, coordinate systems can also be repositioned manually via the navigation bar > ‘Set coordinate system’ action. Each view in DIALux has its own coordinate system. This can be repositioned flexibly for each.

- It is not uncommon for planners to agree on any common insertion point in the project. This does not necessarily have to correspond to the insertion point of the IFC site. Such insertion points are often represented by a small 3D object, such as a cube or prism.

Now it would be advantageous to freely define the insertion point in DIALux on the object. We are working on offering a function to freely position the insertion point (coordinate system) after an import. The coordinates of the exported luminaires will then be based on this insertion point. Until then, DIALux will initially take the insertion point from the IFC terrain.

4 - How do I load Autodesk Revit models into DIALux? 

To load a model from Revit into DIALux, the Revit model must first be exported as an IFC file. You can access the export via File > Export > IFC.
In Revit, it is common practice to merge buildings from different submodels. Each submodel is then available as a separate Revit file. This is referred to as a federated model. If federated Revit models are exported to IFC, the following setting must be checked in Revit:
 
The merged model should be brought together on a single site in the IFC file. Revit offers setting options here. To do this, select "Modify Setup" > "Additional Content" > "Linked Files" > "Export to same Site". 

Otherwise, it can happen that each submodel in the IFC file receives its own site definition. DIALux only ever processes one site definition per IFC file. If an IFC file contains several site definitions, only the first one is imported. It is therefore important to know this setting.
 
Dealing with the 'Building Storey' checkbox
Another important aspect concerns the handling of the ‘Building Story’ checkbox in the elevation profile. In Revit, storeys are defined via section planes. If a lower and upper section plane defines a storey (checkbox ticked), all components in between are assigned to a corresponding storey in the exported IFC model. 
 
However, we have seen cases in which component groups, e.g. handrails, furniture or HVAC, were clearly assigned to a storey from the assembly position, but the ‘Building Story’ checkbox was also selected for these component groups. These components are already subsets of a storey, which are therefore also mapped as a storey in the IFC file. You are then dealing with a storey within a storey. This is unfavourable from an IFC perspective. 

It is therefore necessary to check in Revit what is really a storey. It is better to deselect the checkbox for components that are on a storey. This means that no superfluous storey definitions are created in the IFC model during IFC export to Revit.

5 - What characterises high model quality?

The following tips apply in part to working with DIALux, but are also relevant for other CAD programmes. Overall, the open BIM planning process benefits from high model quality.

open BIM with IFC relies on the virtual construction of a building and requires the same level of accuracy as a real construction.
- Walls should not float, but should be constructed in line with the floor and ceiling (accurate to the millimetre).
- Walls that touch should also be constructed to butt joints. If there are gaps, these are also imported and displayed as such (accurate to the millimetre).
- Components that penetrate other components or protrude into them are also imported and displayed by DIALux in this way.
- Windows and doors are usually located in external or partition walls. The required wall opening can thus be reliably determined.
- Storey floors or ceilings should be present
- Zones and rooms should be clearly defined by spaces 

If an IFC model does not guarantee the above points, this manifests itself in various disadvantages in DIALux:
- Performance problems increase
- Storeys have no floors or ceilings
- Rooms are poorly recognised as such
- The calculation accuracy decreases
- the visualisation becomes unattractive
- visualisation problems increase
- There is a lack of information on statics, material quantities, insulation, etc.

Windows (doors) with wall openings
DIALux determines the corresponding wall openings for windows. Other CAD programmes do not always do this, which is not wrong per se. If a concrete shell wall is constructed, it usually has an opening where windows or doors are positioned. A window manufacturer provides IFC information on the window, but not on the necessary wall opening in the later application. IFC models should clearly define the relationship between the wall opening and the window or door.

If these references are missing in the IFC model, wall openings can no longer be moved correctly using the old method. If the new method is selected in the second step of the IFC import, holes for windows and doors are generally no longer moved.

Materials and colours
It can happen that colours and materials look different between the CAD programs and DIALux. DIALux with its light calculation evaluates information on the reflection of surfaces in the IFC model. Colours look paler in DIALux, for example, because the reflection is included in the representation. This information is always determined from the IFC model.

We have found that CAD programmes sometimes add textures and materials to the representation. When importing, DIALux is strictly orientated to the information it finds in the IFC model.

Correct use of IFC types
Planners who create an IFC building model have it in their hands to use the correct IFC types. If, for example, sanitary facilities (IfcSanitaryTerminal) or lights (IfcLightFixture) are designed in the CAD programme using the furniture tool, the result is furniture (IfcFurniture). DIALux analyses the IFC types when importing and classifies the entire IFC model according to these types. If types are applied incorrectly, the affected objects have no recognisable function in DIALux and are not correctly taken into account for connections and power calculations.
 
For DIALux evo, for example, it is very important that windows are also defined as windows (and not as walls or furniture), as otherwise the influence of daylight cannot be calculated correctly. Façade curtains (IfcCurtainWall), which are actually window fronts, are also frequently constructed.

Which IFC types are supported?
DIALux attempts to import and display all IFC objects of an IFC model. From DIALux evo 12 onwards, information from other trades such as HVAC, sanitary facilities or the electrical installation is also imported and displayed. Each IFC object is checked to see whether it has 3D geometry and material properties. If it does, DIALux displays such IFC objects in the correct place.

Which IFC objects are not supported or ignored?
A few IFC types are currently not supported by DIALux or are ignored in the event of an error.
- The IFC file format recognises various objects for displaying content in 2D that is defined for a floor plan, for example. The IFC import currently only supports 3D content. In practice, it is common to merge IFC models with plans in the respective authoring programme anyway.
- IFC objects without correct 3D geometry are skipped by DIALux during import because they cannot be displayed. If DIALux skips such objects, this is noted as information in the text file.

If components or data in the IFC model are faulty, DIALux will attempt to skip the faulty data and import the error-free part of the model. This may be the reason why components are missing in DIALux after the import!

Which IFC versions are supported?

The IFC format version 2x3 TC1 is supported on the import side. New from DIALux evo 12 is also partial IFC 4 support. IFC 4 introduces a new description of 3D geometry. We do not yet fully support this new format. However, there are enough cases in which IFC 4 files fall back on the description format of IFC 2x3. The combination of an IFC 4 file with an IFC 2x3 geometry format is imported. This is important to know in order to export the appropriate IFC version for DIALux in the IFC tools.

Helpful export settings in CAD programmes
DIALux prefers geometries as BREP (Boundary Representation, description of objects by their boundary surfaces). Evo copes better with non-triangulated surfaces. The surfaces should be correctly oriented and form a closed volume, which unfortunately is not a matter of course in many CAD programmes. If the CAD programme allows export settings of this kind, this supports the import into DIALux.
- Multi-layer construction elements: These building elements should not be separated into individual objects.
- Elements in Solid Element Operations: Yes, as BREP
- Elements with connections : Yes, as BREP
- Slabs with inclined side face(s): Yes, as BREP
- IFC terrain information: Yes, as BREP
- IFC site location: at the project origin

6 - What to do if IFC models are too cumbersome for the computer and/or DIALux?

Basically, the more complex the IFC model, the greater the impact on performance when working in DIALux. If DIALux cannot import a building model, there are ways to reduce the complexity.
- The content of the IFC model is reduced. DIALux does not force anyone to plan an entire building. Especially if it is very complex. An IFC file can also only contain a partial model of a building, e.g. only one floor etc. The building is thus divided into several IFC submodels.
- As of DIALux evo 12, a wizard can be used to select which information is to be imported from the IFC model. The entire building structure (spatial structure) with all floors and their contents is listed here. Planners can simply deselect entire floors or only contents within the floors. It is thus possible to import buildings without building equipment or furnishings. Even windows and doors can be deselected in order to calculate only the artificial light in closed rooms.

7 - FAQ
- Where can I find help with the DIALux Pro purchase process?
Here is a detailed page for: https://www.dialux.com/en-GB/faq

- Can I save and reuse IFC components for future planning?
As of DIALux 13.1, IFC components can be saved as a DIALux furniture file by right-clicking. Once saved, these components can then be reused as often as required. Furniture files are only ever upwards compatible. Furniture files from a higher DIALux version cannot be loaded into a lower DIALux version.
