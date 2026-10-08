# Why is the documentation empty oder all items are shown greyed out?

> 分类：Solution home / Documentation / Troubleshooting ｜ 更新：Wed, 10 Jan, 2024 at 11:18 AM
> 来源：https://evo.support-en.dial.de/support/solutions/articles/9000066289-why-is-the-documentation-empty-or-all-items-are-shown-greyed-out-

Probably a service on the PC is deactivated, which is responsible for the administration of the manufacturer information and the communication with the external process for generating the documentation.
This is the DCF (DIAL Communication Framework), which must be restarted. 
Under Control Panel --> Administrative Tools --> Services the service "DIAL Communication Service" should be listed. The start type should be set to "Manual", then the service will be automatically started and stopped again by DIALux or the manufacturer catalogues as needed.
