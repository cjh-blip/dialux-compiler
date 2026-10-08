# Error message during opening an evo project

> 分类：Solution home / Opening & Saving of evo files / Project file ｜ 更新：Wed, 7 Apr, 2021 at 10:06 AM
> 来源：https://evo.support-en.dial.de/support/solutions/articles/9000097276-error-message-during-start-of-an-evo-project

If the error message below appears while loading an evo project, please proceed as follows:
 
Please check if you have all necessary read and write permissions for the directory (including all subdirectories) in Windows: "C:\Users\<Username>\AppData\Local\DIAL GmbH\DIALux\".
The user must first navigate to the directory C:\Users\<Username>\AppData\Local\DIAL GmbH\DIALux\.
In the case of user accounts without administration rights, a UAC (User Account Control) window may appear at the position C:\Users\User.
There the user must enter the password of the administrative user account to access the above-mentioned directory.

If the problem persists, you could temporarily disable the antivirus scanner until the project could be loaded.

System.UnauthorizedAccessException
Access to the path 'C:\Users\User name\AppData\Local\DIAL GmbH\DIALux\DIALuxProjectTemp\......\Project\Address\a66261fd-4527-4c4d-96a8-1f446e975a87\.......tmp.tmp' is denied.
at System.IO.__Error.WinIOError(Int32 errorCode, String maybeFullPath)
at System.IO.FileStream.Init(String path, FileMode mode, FileAccess access, Int32 rights, Boolean useRights, FileShare share, Int32 bufferSize, FileOptions options, SECURITY_ATTRIBUTES secAttrs, String msgPath, Boolean bFromProxy, Boolean useLongPath, Boolean checkHost)
at System.IO.FileStream..ctor(String path, FileMode mode, FileAccess access, FileShare share, Int32 bufferSize, FileOptions options, String msgPath, Boolean bFromProxy)
at System.IO.FileStream..ctor(String path, FileMode mode)
at Ionic.Zip.ZipEntry.InternalExtract(String baseDir, Stream outstream, String password)
at Ionic.Zip.ZipFile._InternalExtractAll(String path, Boolean overrideExtractExistingProperty)
at Dial.Dialux.Classlib.Persistence.ProjectTempFolderManager.UnZip(FileInfo archive, String target, IProgressInput progress)
at Dial.Dialux.InteractionFileHandling.LoadSave.LoadSaveManager.UnzipProjectArchive(FileInfo fileInfo, IStorage& projectStorage)
at Dial.Dialux.InteractionFileHandling.LoadSave.LoadSaveManager.LoadProject(FileInfo fileInfo)
at Dial.Dialux.InteractionProjectHandling.Base.ProjectHandling.LoadProject(String filename)
at Dial.Dialux.Gui.MainWindowFileHandling.OpenFile(String filename)
at Dial.Dialux.Gui.MainWindowFileHandling.OnCommandOpen(Object sender, ExecutedRoutedEventArgs e)
at System.Windows.Input.CommandBinding.OnExecuted(Object sender, ExecutedRoutedEventArgs e)
at System.Windows.Input.CommandManager.ExecuteCommandBinding(Object sender, ExecutedRoutedEventArgs e, CommandBinding commandBinding)
at System.Windows.Input.CommandManager.FindCommandBinding(CommandBindingCollection commandBindings, Object sender, RoutedEventArgs e, ICommand command, Boolean execute)
at System.Windows.Input.CommandManager.FindCommandBinding(Object sender, RoutedEventArgs e, ICommand command, Boolean execute)
at System.Windows.Input.CommandManager.OnExecuted(Object sender, ExecutedRoutedEventArgs e)
at System.Windows.RoutedEventArgs.InvokeHandler(Delegate handler, Object target)
at System.Windows.EventRoute.InvokeHandlersImpl(Object source, RoutedEventArgs args, Boolean reRaised)
at System.Windows.UIElement.RaiseEventImpl(DependencyObject sender, RoutedEventArgs args)
at System.Windows.Input.RoutedCommand.ExecuteImpl(Object parameter, IInputElement target, Boolean userInitiated)
at System.Windows.Input.CommandManager.TransferEvent(IInputElement newSource, ExecutedRoutedEventArgs e)
at System.Windows.RoutedEventArgs.InvokeHandler(Delegate handler, Object target)
at System.Windows.EventRoute.InvokeHandlersImpl(Object source, RoutedEventArgs args, Boolean reRaised)
at System.Windows.UIElement.RaiseEventImpl(DependencyObject sender, RoutedEventArgs args)
at System.Windows.Input.RoutedCommand.ExecuteImpl(Object parameter, IInputElement target, Boolean userInitiated)
at System.Windows.Controls.MenuItem.InvokeClickAfterRender(Object arg)
at System.Windows.Threading.ExceptionWrapper.InternalRealCall(Delegate callback, Object args, Int32 numArgs)
at MS.Internal.Threading.ExceptionFilterHelper.TryCatchWhen(Object source, Delegate method, Object args, Int32 numArgs, Delegate catchHandler)
