# Exchange of data from CAD programs to DIALux and back again

> 分类：Solution home / General information / Interfaces ｜ 更新：Tue, 16 Jan, 2024 at  6:14 PM
> 来源：https://evo.support-en.dial.de/support/solutions/articles/9000073210-data-exchange-between-cad-programs-and-dialux

Lighting design is an integral element of the building design process. The building is created in the CAD system. The architect sets the room geometry. Walls emerge, windows and wall openings are planned and the whole building develops virtually. At some stage it is the turn of lighting design. It is frequently very time intensive when a building or room geometry has to be entered anew in DIALux. This is in fact a superfluous step since this information is already available in digital form. 
 
Since DIALux 1.0 DIAL has defined an interface to CAD programs and made this available to the manufacturers of CAD programs. Current approaches to the topic of data exchange are being discussed under the catchword under the slogan "BIM". The term BIM stands for „Building Information Modelling“ and describes a software-supported approach to optimized planning, and the implementation and operation of buildings. The aim is to gather all the data related to the building and its components and to combine them and integrate them in a network. In this way the "virtual building" is captured completely in digital form and can be visualized.

These data are stored in a standardized, open data model and are thus available for exchange between different programs. 

Unfortunately, at present, not every project is planned as a BIM model and for many applications the volume of data in a BIM model is much too large. For this reason alongside the actual BIM format, IFC, simplified data models have established themselves, which describe for example only the building shell. Here mention can be given, for example, to the gbXML interface. 
 
Further information: www.buildingsmart.com and www.gbxml.org 
 
DIALux has integrated the STF interface and the gbXML interface as exchange formats. The STF interface developed by DIAL defines the data transfer for the building shell. The architect defines the building in the CAD program, exports the room geometry, the room designation, the windows and door positions and, if available, specified luminaire positions. These are then transferred to DIALux via a STF file. The lighting designer reads in the STF file and finds the rooms defined by the architect ready and waiting in DIALux. The lighting designer can focus on his core task. Instead of reconstructing all the rooms again, he can develop the lighting concept, select the luminaires and position these accordingly in the rooms. After completion of the planning and calculation process the result is returned to the CAD program via the STF interface. Luminaires, with their positions and technical data, images, texts and calculation results can be adopted by the CAD software and work can continue. The STF interface is supported by many CAD and TGA programs. Check whether your CAD might simplify your work by means of STF. If not, then please pass on your wishes to us. It is your time. 
 
DIAL now has two excellent lighting design programs on the market: DIALux und DIALux evo. In DIALux, in accordance with the old school of lighting design, rooms were seen as individual elements for photometric planning. Each room stood on its own. DIALux evo takes account of the whole architecture of the building. As in reality, it is possible in DIALux evo to plan the whole building completely, even a complex of several buildings with both indoor and outdoor spaces. 
DIALux evo is still quite young and not all the functionalities planned have been integrated yet. Nevertheless, it is already a high-performance design tool. Below, you will find a list of the interfaces of both programs:
 
Function
DIALux
DIALux evo

DWG/ DXF import
available
available

DWG/DXF export
available
available

STF import
available
available

STF export
available
in preparation

gbXML import
available
planned

The design process using the STF interface might look like this, for example:
- The architect creates the building in his CAD software. For lighting design the building or individual rooms are exported into STF.
- The lighting designer receives from the architect information about the rooms, e.g. walls, windows, doors, and perhaps information about where the luminaires were previously positioned (keyword: refurbishment).
- After importing the STF file, the lighting designer finds all these information in DIALux. No room needs to be reconstructed. 
- Issues relevant to lighting design such as calculation objects or furniture can be completed in DIALux.
- The lighting designer selects the luminaires and lamps from the manufacturers' electronic catalogues and inserts these into his plan.
- After calculating and completing the lighting design, the designer exports all the information back to the STF file.
- The electrician/ architect receives exact details about the products used and the results of the lighting design (illuminance, power input, energy consumption etc.).

Some of the programs which support the STF interface are listed here (in alphabetical order, with no guarantee that this is complete):
 
Manufacturer
Name of program
Link

A&A Co. Ltd.
Vectorworks

ALPI
Caneco Implantation

ArCADia
ArCADiasoft 

Bentley
Bentley elcoCAD

CADLINE Software S.R.L
GEAR

 CADprofi
CADprofi

Graphisoft Building Systems
DDS CAD Elektro

ESS
AX3000

IBS Döbeln
LVZ ElektroCAD

Intersoft
ArCADia

Kyle T. Morin
Revit-DIALux STF Exporter

linear GmbH
liNear

 pit - cup
 pit - CAD
 
MagiCAD Group
MagiCAD

Sapr-Alpha
Alpha SE

Trimble 
Trimble Nova 

Trace Software International
Elec Calc EP

…
…

…
…

Manufacturers of CAD software who would like to integrate the STF interface into their program are invited to contact DIAL. You can get in touch with your contact at: bremecker@dial.de.
We would be pleased to send you the latest documentation on the interface free of charge.
