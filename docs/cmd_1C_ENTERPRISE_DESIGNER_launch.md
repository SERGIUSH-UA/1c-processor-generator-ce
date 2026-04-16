Параметры выбора режима запуска

Одновременное использование параметров из приведённой ниже таблицы не допускается.
DESIGNER  (CONFIG в 8.0) Запуск в режиме Конфигуратора.
ENTERPRISE   Запуск в режиме Предприятия.
CREATEINFOBASE [/AddInList [ИмяИБ]] [/UseTemplate [имя файла шаблона]]   Создание информационной базы.     
•    СтрокаСоединения - обязательный параметр, см. ниже.
•    /AddInList [ИмяИБ] - имя, под которым база добавляется в список. Если этот параметр не указан, база добавлена в список не будет. Если не указано ИмяИБ, будет задано имя по умолчанию (как при интерактивном создании базы).
•    /UseTemplate — создание информационной базы осуществляется по шаблону, указанному в [имя файла шаблона]. В качестве шаблонов могут быть файлы конфигурации (.cf) или файлы выгрузки информационной базы (.dt). Если шаблон не указан, параметр игнорируется.

Параметры командной строки выбора режима

DESIGNER [<список параметров запуска>]  — запуск системы 1С:Предприятие 8 в режиме "Конфигуратор".
 <Список параметров запуска>
 	 
 	 <Общие параметры запуска>  [<Параметры пакетного режима>]
 	 	 	 
 	
 [Параметры запуска конфигуратора] |
 [Регистрация 1С:Предприятия 8 в качестве OLE-Automation-сервера]
 
ENTERPRISE [<список параметров запуска>] — запуск системы 1С:Предприятие 8 в режиме "1С:Предприятие".
 <Список параметров запуска>
 
 Общие параметры запуска


CREATEINFOBASE <строка соединения> [/AddToList [<имя ИБ>]] [/DisableStartupDialogs] [/UseTemplate <имя файла шаблона>] [/Out <имя файла>] [/L] [/VL] [/O] [/DumpResult <имя файла>] — создание информационной базы.
<Строка соединения> — строка, задающая параметры информационной базы, каждый из которых представляет собой фрагмент вида <Имя параметра>=<Значение>, где:
<Строка соединения> — строка, задающая параметры информационной базы, каждый из которых представляет собой фрагмент вида <Имя параметра>=<Значение>, где:
Имя параметра — имя параметра; 
Значение — его значение.
/AddToList — параметр, показывающий, под каким именем добавлять базу в список, если не указан, база не будет добавлена в список.
<имя ИБ> — имя информационной базы, под которым сведения о базе будут добавлены в список информационных баз. Если не указано, используется имя по умолчанию, аналогичное имени, предлагаемому системой при интерактивном создании информационной базы.
/DisableStartupDialogs — отключает вызов диалоговых окон. Если не указано, то в процессе запуска пользователю будут выдаваться различные сообщения (например, запрос пароля администратора кластера при создании новой информационной базы).
/UseTemplate — создание информационной базы осуществляется по шаблону, указанному в <имя файла шаблона>. В качестве шаблонов могут быть файлы конфигурации (.cf) или файлы выгрузки информационной базы (.dt). Если шаблон не указан, параметр игнорируется.
/Out <имя файла> [-NoTruncate]] — установка файла для вывода служебных сообщений. Если задан параметр -NoTruncate (через пробел), файл не очищается. 
Во время исполнения пакетных команд файл сообщений можно открыть для просмотра. Запись сообщений в файл не буферизуется (сообщения записываются сразу). —
/L <код языка> — код языка интерфейса платформы. Список доступных языков интерфейса см. здесь.
/VL <код локализации сеанса> — указывается код локализации сеанса, используемый при форматировании данных типа Число и Дата, а также в методах ЧислоПрописью() и ПредставлениеПериода().
/O <скорость соединения> — определяет скорость соединения (используется в тонком и веб-клиенте):
 Normal — обычная, 
 Low — низкая скорость соединения.
/DumpResult <имя файла> —  предназначен для записи результата создания информационной базы в файл. После параметра должно быть указано имя файла. Результат - число (0 - в случае успеха).
Пример: 
       CREATEINFOBASE File=e:\test3; /AddToList TEST33 /UseTemplate "C:\Documents and Settings\User\My Documents\tmplts\TestVendor\TestConfig\1Cv8.cf"
Одновременное использование параметров не допускается.


Общие параметры запуска

В данном разделе приводятся общие параметры запуска:
Указание параметров подключения

/F,
/IBConnectionString,
/IBName,
/O,
/S,
/WS,
/SLev,
/Z.
Настройка аутентификации

/Authoff,
/N,
/NoProxy,
/OIDA,
/P,
/Proxy,
/SAOnRestart,
/WA,
/WSA,
/WSN,
/WSP.
Определение режима запуска

/AppArch,
/AppAutoCheckVersion,
/AppAutoCheckMode ,
/MainWindowMode,
/RunModeManagedApplication,
/RunModeOrdinaryApplication.
Использование клиентских сертификатов (только для тонкого клиента)

/HttpsCA,
/HttpsCert,
/HttpsForceTLS1_0,
/HttpsForceTLS1_1,
/HttpsForceTLS1_2. 
Настройки интерфейса

/DisableHomePageForms,
/iTaxi,
/itdi,
/TechnicalSpecialistMode.
Настройки локализации

/L,
/VL.
Настройки отладки

/Debug,
/DebuggerURL,
/DisplayPerformance,
/SimulateServerCallDelay.
Настройки тестирования

/TestClient,
/TestManager,
/UILogRecorder.
Проверки во время работы клиентского приложения

/EnableCheckExtensionsAndAddInsSyncCalls,
/EnableCheckModal,
/EnableCheckServerCalls,
/EnableCheckScriptCircularRefs.
Прочие параметры

/@,
/AllowExecuteScheduledJobs,
/AppAutoInstallLastVersion,
/C,
/ClearCache,
/DisableStartupDialogs,
/DisableStartupMessages,
/DisplayUserNotificationList,
/Execute,
/Out,
/RunShortcut,
/TComp,
/UC,
/URL,
/UseHwLicenses,
/UsePrivilegedMode.
 

 Параметры запуска конфигуратора в пакетном режиме

Внимание! Если в параметре командной строки требуется ввести имя файла, то следует учитывать, что при указании имени файла с полным путем все каталоги, входящие в состав пути, должны существовать.
Строка запуска системы "1С:Предприятие" в режиме Конфигуратор имеет вид:
1cv8 DESIGNER [<параметры запуска>]
Коды возврата

Команды пакетного режима запуска возвращают один из следующих кодов возврата:
0 - команда выполнена успешно.
1 - при выполнении команды произошла ошибка.
101 - при выполнении команды обнаружены ошибки в данных.
Выгрузка и загрузка информационной базы

/DumpIB,
/RestoreIB.
Восстановление структуры информационной базы

/IBRestoreIntegrity.
Конфигурация и расширения

/CheckCanApplyConfigurationExtensions,
/CompareCfg,
/DeleteCfg,
/DumpCfg,
/DumpConfigFiles,
/DumpConfigToFiles,
/DumpDBCfg,
/DumpDBCfgList,
/LoadCfg,
/LoadConfigFiles,
/LoadConfigFromFiles,
/MergeCfg,
/RollbackCfg,
/UpdateDBCfg.
Проверки конфигурации и расширений

/CheckConfig,
/CheckModules,
/IBCheckAndRepair,
/CheckCanApplyConfigurationExtensions.
Поддержка конфигурации

/ManageCfgSupport,
/UpdateCfg.
Команды создания файла поставки и обновления

/CreateDistributionFiles,
/CreateDistributivePackage, 
/CreateDistributive (Не рекомендуется!),
/CreateTemplateListFile,
/SignCfg.
Внешние обработки (отчеты)

/DumpExternalDataProcessorOrReportToFiles,
/LoadExternalDataProcessorOrReportFromFiles.
Мобильное приложение

/MobileAppUpdatePublication,
/MobileAppWriteFile.
Мобильный клиент

/MobileClientDigiSign,
/MobileClientWriteFile.
Журнал регистрации

/ReduceEventLogSize.
Удаление данных

/EraseData.
Предопределенные данные

/SetPredefinedDataUpdate.
Распределенная информационная база

/ResetMasterNode.
Команды работы с хранилищем конфигурации

/ConfigurationRepositoryF,
/ConfigurationRepositoryN,
/ConfigurationRepositoryP,
/ConfigurationRepositoryCreate,
/ConfigurationRepositoryAddUser,
/ConfigurationRepositoryCopyUsers,
/ConfigurationRepositoryCommit,
/ConfigurationRepositoryLock,
/ConfigurationRepositoryUnlock,
/ConfigurationRepositoryBindCfg,
/ConfigurationRepositoryUnbindCfg,
/ConfigurationRepositoryDumpCfg,
/ConfigurationRepositoryUpdateCfg,
/ConfigurationRepositorySetLabel,
/ConfigurationRepositoryReport,
/ConfigurationRepositoryOptimizeData,
/ConfigurationRepositoryClearCache,
/ConfigurationRepositoryClearGlobalCache,
/ConfigurationRepositoryClearLocalCache.
Команды работы в режиме агента

/@,
/AgentBaseDir,
/AgentMode,
/AgentPort,
/AgentListenAddress,
/AgentSSHHostKey,
/AgentSSHHostKeyAuto.
Прочие параметры

/ConvertFiles,
/DumpResult,
/DisableHomePageForms,
/DisableLocalSpeechToText,
/DisableSplash,
/DisableStartupDialogs,
/DisableStartupMessages,
/DisableUnrecoverableErrorMessage,
/DisplayUserNotificationList,
/RunEnterprise,
/UseHwLicenses,
/Visible
/Out

LoadExternalDataProcessorOrReportFromFiles

/LoadExternalDataProcessorOrReportFromFiles <путь к корневому файлу выгрузки> <путь к файлу внешней обработки или отчета>
— загрузка внешних обработок или отчетов из файлов. Все параметры являются обязательными:
<путь к корневому файлу выгрузки> — содержит путь к корневому файлу выгрузки внешний обработки или отчета в формате XML.
<путь к файлу внешней обработки или отчета> — содержит путь к файлу внешней обработки или отчета, в который будет записан результат загрузки из XML-файла. Расширение результирующего файла всегда соответствует содержимому исходной выгрузки: ".epf" — для внешних обработок, ".erf" — для отчетов. Если в качестве параметра задан файл с другим расширением, то оно будет заменено на соответствующее.
Дополнительно можно указать адрес строки подключения к информационной базе, например, с помощью ключа /IBName. При этом, если во внешней обработке есть внешние ссылки, они будут разрешаться относительно указанной информационной базы. Если информационная база не указана, внешние ссылки разрешаться не будут.

AgentMode

/AgentMode 
– включает режим агента конфигуратора. При наличии этого ключа игнорируются ключи /DisableStartupMessages и /DisableStartupDialogs, если таковые указаны.

@

/@ <имя файла>
— параметры командной строки записаны в указанном файле.

/Visible

— делает исполнение пакетной команды видимым пользователю. На время работы конфигуратора открывается окно заставки. Если конфигуратор запущен в режиме агента, отображает окно статуса.

/DumpResult — предназначен для записи результата работы конфигуратора в файл. После ключа должно быть указано имя файла. Результат - число (0 - в случае успеха).

/ConvertFiles [имя файла|каталога]  параметр пакетной конвертации файлов 1С 8.x.
Если задан каталог, осуществляется конвертация всех доступных документов в указанном каталоге и вложенных каталогах. Для успешной конвертации файлы должны быть доступны для записи. Если указанный в качестве параметра файл недоступен для записи, выдается сообщение об ошибке. В случае режима работы с каталогом, недоступные для записи файлы пропускаются без выдачи сообщений об ошибке.
Для работы данного механизма должен быть запущен режим "Конфигуратор" и открыта конфигурация, в среде которой будет производиться конвертация. Имя информационной базы и параметры авторизации можно указать через стандартные параметры командной строки. В случае отсутствия таких параметров, будут выданы соответствующие запросы, как и в других аналогичных механизмах командной строки, работающих в режиме "Конфигуратор".

Пример:
Конвертация файла:  1cv8.exe /ConvertFilesd:/base/ExtProcessing.epf
Конвертация каталога:  1cv8.exe /ConvertFilesd:/base