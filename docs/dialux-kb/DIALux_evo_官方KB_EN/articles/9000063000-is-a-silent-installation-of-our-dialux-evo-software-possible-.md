# Is a "silent" installation of our DIALux evo software possible?

> 分类：Solution home / Installation evo / Miscellaneous ｜ 更新：Tue, 14 Feb, 2023 at  2:40 PM
> 来源：https://evo.support-en.dial.de/support/solutions/articles/9000063000-is-a-silent-installation-of-our-dialux-evo-software-possible-

Starting with our evo version 7.1 a "silent" installation is possible, because we do not use a combined setup anymore.

Our DIALux evo software can now be installed and uninstalled "silently". If an older evo version is already installed, it will automatically be uninstalled "silent" before the new evo version is installed.

The DIAL Data Dispatcher (DDD) can also be uninstalled from version 8.0 with the following line:

"C:\Program Files (x86)\DIAL GmbH\Data Dispatcher\uninstall.exe" "/U:C:\Program Files (x86)\DIAL GmbH\Data Dispatcher\Uninstall\uninstall.xml" /s""

The setting "%DontEnforceRequirements%=1" in the configuration file also prevents the setup from aborting if no OpenGL driver is available. 

With the setting "%LogFolder%" it is possible to define in which directory the log file is stored, e.g. "%LogFolder%="C:\Logfiles"". Important: No backslash at the end and the directory must exist.

Usage:

Start command prompt as admin!

Installation: <Setup.exe> /s:<configfile> (Example: evo7.1setup.exe /s:c:\silentsetup.ini)

Here is a sample file: Silentsetup.ini

Parameter in the configuration file: 
Installation path, name of the start menu folder, option if the setup is executed without restart (0 => restart during setup, 1 => no restart).

We recommend to execute the setup only without reboot during the setup and to reboot the system once after the setup if necessary. Restarts during setup may be problematic.

Further information: https://www.indigorose.com/webhelp/suf70/Program_Reference/Command_Line_Options.htm
