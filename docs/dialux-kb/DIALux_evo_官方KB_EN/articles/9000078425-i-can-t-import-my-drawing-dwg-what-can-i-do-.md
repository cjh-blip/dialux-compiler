# I can't import my drawing/DWG. What can I do?

> 分类：Solution home / Construction / Drawings/DWG import ｜ 更新：Thu, 24 Mar, 2022 at  1:14 PM
> 来源：https://evo.support-en.dial.de/support/solutions/articles/9000078425-i-can-t-import-my-drawing-dwg-what-can-i-do-

1) The following information appears during the import:

 In your DWG there are one or more .SHX files that were created as external references when saving the DWG file. This creation of external references must be avoided when saving the DWG, as our evo software cannot process such references.

You can try to include these references as a block in a CAD software and/or clean up the drawing.

It is also possible to download and install the CAD software DraftSight.

As soon as you have loaded the DWG drawing into DraftSight, you must open the context menu in the "References" tab by right-clicking. There you will find an entry "Detach" in the menu. When you execute this command, the external reference is removed and the DWG file should now be able to be imported into our evo software. You have to do this with all references.

In the following screenshots, the CAD programme DraftSight 2016 was used. 

2) Open the problematic DWG file in a CAD programme and execute the "Resolve" function there several times. Then save the DWG as a 2010 AutoCAD version and import this DWG into evo again. 
In the following screenshots, the CAD programme DraftSight 2016 was used.
