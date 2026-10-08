# Tips for an IFC export of the lighting system

> 分类：Solution home / Import / Export / Export ｜ 更新：Wed, 20 Mar, 2024 at  5:21 PM
> 来源：https://evo.support-en.dial.de/support/solutions/articles/9000236980-tips-for-an-ifc-export-of-the-lighting-system

DIALux's IFC export focusses on the 3D model of the lighting system. Such a lighting system including description is exported to a separate IFC file, which can later be merged with other trades in a collaboration solution (CDE - Common Data Environment) or imported into other CAD software.
 
As soon as luminaires are planned in the project, the IFC model can be exported to an IFC file via the mode Export, Tool IFC Model. DIALux evo currently exports the entire lighting system to an IFC file. A few export settings are planned for the future.

Result of an exported IFC model as an example in the DDScad Viewer.

Which IFC versions are offered?
- As DIALux evo currently fully supports IFC 2x3 on the import side, the IFC version for export is also limited to IFC 2x3.

Which file formats can I export?
- *.ifc and additionally as compressed (*.zip)
- *.ifcxml and additionally as compressed (*.zip)
 
What 3D information is exported and how?
- 3D model of all "drawn" luminaires at their position (see above)
- Especially for aligned luminaires (with joints), a 3D model in its final aligned state
- Each luminaire is structurally assigned to its storey. The IFC structure is determined from the architectural model. The lighting system is therefore structurally synchronied to an architectural model. The IFC export also determines the reference coordinate system (terrain) from the architectural model. The lighting system is transformed into this reference coordinate system so that the architectural model and the model of the lighting system can later be overlaid in 3D.
- The appropriate length units are determined from the architectural model and adopted by the IFC export.
 
Which properties are exported for each luminaire?
- Article name
- Article number
- Article description
- Luminaire manufacturer
- Mounting type
- Reference surface (floor, wall, ceiling)
- Emergency lighting operation possible (yes/no) Product feature
- Total system connected load (sum of all light sources in the luminaire)
