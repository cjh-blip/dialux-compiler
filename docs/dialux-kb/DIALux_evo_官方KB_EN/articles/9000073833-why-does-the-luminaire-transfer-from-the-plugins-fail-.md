# Why is it not possible to send luminaires to DIALux?

> 分类：Solution home / Light / DIALux PlugIns ｜ 更新：Thu, 22 Apr, 2021 at  2:57 PM
> 来源：https://evo.support-en.dial.de/support/solutions/articles/9000073833-why-does-the-luminaire-transfer-from-the-plugins-fail-

Probably a service on the PC is deactivated, which is responsible for the administration of the manufacturer information and the communication with the external process for generating the documentation.
This is the DCF (DIAL Communication Framework), which must be restarted. 
Under Control Panel --> Administrative Tools --> Services the service "DIAL Communication Service" should be listed. The start type should be set to "Manual", then the service will be automatically started and stopped again by DIALux or the manufacturer catalogues as needed.
