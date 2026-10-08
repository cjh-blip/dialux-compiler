# Evo starts with Exception

> 分类：Solution home / Opening & Saving of evo files / Project file ｜ 更新：Wed, 7 Apr, 2021 at 10:08 AM
> 来源：https://evo.support-en.dial.de/support/solutions/articles/9000108747-evo-starts-with-an-exception

If you receive the error message below when starting evo, the cause of this problem may be a missing Microsoft patch. Therefore we would like to recommend you to install the MS patch according to your operating system. Please use the following link to do so:
https://support.microsoft.com/en-us/help/2999226/update-for-universal-c-runtime-in-windows

Unbehandelte Ausnahme: Exception has been thrown by the target of an invocation.
System.Reflection.TargetInvocationException
Exception has been thrown by the target of an invocation.
at System.RuntimeMethodHandle.InvokeMethod(Object target, Object[] arguments, Signature sig, Boolean constructor)
at System.Reflection.RuntimeMethodInfo.UnsafeInvokeInternal(Object obj, Object[] parameters, Object[] arguments)
at System.Reflection.RuntimeMethodInfo.Invoke(Object obj, BindingFlags invokeAttr, Binder binder, Object[] parameters, CultureInfo culture)
at Dial.Dialux.Classlib.Tools.ModuleLoader.InitializeModules(IEnumerable`1 modules, Action preDelayedInitAction)
at Dial.Dialux.Gui.DIALuxModuleLoader.InitializeModules()
at Dial.Dialux.Gui.MainWindow.OnLoaded(Object sender, RoutedEventArgs e)
at System.Windows.EventRoute.InvokeHandlersImpl(Object source, RoutedEventArgs args, Boolean reRaised)
at System.Windows.UIElement.RaiseEventImpl(DependencyObject sender, RoutedEventArgs args)
at System.Windows.BroadcastEventHelper.BroadcastEvent(DependencyObject root, RoutedEvent routedEvent)
at System.Windows.BroadcastEventHelper.BroadcastLoadedEvent(Object root)
at MS.Internal.LoadedOrUnloadedOperation.DoWork()
at System.Windows.Media.MediaContext.FireLoadedPendingCallbacks()
at System.Windows.Media.MediaContext.FireInvokeOnRenderCallbacks()
at System.Windows.Media.MediaContext.RenderMessageHandlerCore(Object resizedCompositionTarget)
at System.Windows.Media.MediaContext.RenderMessageHandler(Object resizedCompositionTarget)
at System.Windows.Threading.ExceptionWrapper.InternalRealCall(Delegate callback, Object args, Int32 numArgs)
at System.Windows.Threading.ExceptionWrapper.TryCatchWhen(Object source, Delegate callback, Object args, Int32 numArgs, Delegate catchHandler)

Inner Exception:
System.IO.FileNotFoundException
Could not load file or assembly 'Dial.Communication.Net.dll' or one of its dependencies. The specified module could not be found.
at Dial.Dialux.PluginManager.ModuleInit.Init()
at Dial.Dialux.PluginManager.Module.Initialize()
