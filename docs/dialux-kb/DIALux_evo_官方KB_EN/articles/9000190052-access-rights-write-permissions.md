# Access rights/write permissions

> 分类：Solution home / Installation evo / Access rights/write permissions ｜ 更新：Wed, 7 Apr, 2021 at 10:11 AM
> 来源：https://evo.support-en.dial.de/support/solutions/articles/9000190052-access-rights-write-permissions

Basically, the access rights of our DIALux evo software behave as follows: 

Write permissions are only required where a normal user (not admin) usually has write permissions => In the user directory (or "C:\Users\<UserName>\AppData\Local\DIAL GmbH\DIALux\").

In the application directory "C:\Program Files\DIAL GmbH" no write rights are necessary, since writing to this directory is only done during the installation.

The setup takes care that the access rights for all other folders are set accordingly for all users (group "All" or "Users"). 

No admin rights are required to start our DIALux evo software. We also do not recommend to run our DIALux evo software as admin:

- This is much less secure than a less restricted user, because in this case our DIALux evo software really has admin rights on the computer including all security problems that this might cause.

- If our DIALux evo software creates, for example, folders or files while "Run as Administrator" is being used, it may happen that the folders/files are then assigned the access rights for the administrator group as well and normal users cannot access them easily.

Of course, it is possible that companies/customers change the standard rights of Windows and restrict the user accounts extremely, so that, for example, users are neither in the "Users" group nor have write access to their own user directory. In this case, it may be necessary to (selectively) enable this again so that our DIALux evo software will work again. In this case, however, the respective administrator must know which rights he has restricted and must grant them again.

In any case, we have always needed read/write rights in these folders: 

- "C:\ProgramData\DIAL GmbH\DIAL Communication Framework"

- "C:\ProgramData\DIAL GmbH\DIALux" 

But even for these two folders it should be configured after setup so that every user has read and write access to them. This is ensured by the evo setup.
