# UI Patterns Library - 1C Processor Generator

Ready-to-use UI patterns for common scenarios.

---

## Pattern 1: Simple Input Form

**Use case:** User fills a few fields and submits

**Structure:** InputFields → Button

```yaml
processor:
  name: ДанныеКонтрагента
  synonym_ru: Данные контрагента
  synonym_uk: Дані контрагента

attributes:
  - name: Наименование
    type: string
    length: 200
  - name: ИНН
    type: string
    length: 12
  - name: Email
    type: string
    length: 100

forms:
  - name: Форма
    default: true
    events:
      OnOpen: ПриОткрытии
    commands:
      - name: СохранитьДанные
        title_ru: Сохранить
        title_uk: Зберегти
        handler: СохранитьДанные
        shortcut: Ctrl+S
      - name: ОтменаФормы
        title_ru: Отмена
        title_uk: Скасувати
        handler: ОтменаФормы
    elements:
      - type: InputField
        name: НаименованиеПоле
        attribute: Наименование
      - type: InputField
        name: ИННПоле
        attribute: ИНН
      - type: InputField
        name: EmailПоле
        attribute: Email
      - type: UsualGroup
        name: КнопкиГруппа
        group_direction: Horizontal
        child_items:
          - type: Button
            name: СохранитьКнопка
            command: СохранитьДанные
          - type: Button
            name: ОтменаКнопка
            command: ОтменаФормы
```

**handlers/СохранитьДанные.bsl:**
```bsl
Если НЕ ЗначениеЗаполнено(Объект.Наименование) Тогда
    Сообщить("Заполните наименование!");
    Возврат;
КонецЕсли;

СохранитьДанныеНаСервере();
```

---

## Pattern 2: Report with Filters and Table

**Use case:** User sets filter criteria, generates report, views results in table

**Structure:** Filter Group → Generate Button → Results Table

```yaml
processor:
  name: ОтчетПоПродажам
  synonym_ru: Отчет по продажам
  synonym_uk: Звіт по продажах

attributes:
  - name: ДатаНачала
    type: date
    synonym_ru: Дата начала
    synonym_uk: Дата початку

  - name: ДатаОкончания
    type: date
    synonym_ru: Дата окончания
    synonym_uk: Дата закінчення

  - name: Контрагент
    type: CatalogRef.Контрагенты
    synonym_ru: Контрагент
    synonym_uk: Контрагент

forms:
  - name: Форма
    default: true
    properties:
      title: true
      title_ru: Отчет по продажам
      title_uk: Звіт по продажах
    events:
      OnOpen: ПриОткрытии
    value_tables:
      - name: Результаты
        title_ru: Результаты
        title_uk: Результати
        columns:
          - name: Месяц
            type: string
            length: 20
            synonym_ru: Месяц
            synonym_uk: Місяць
          - name: Контрагент
            type: string
            length: 200
            synonym_ru: Контрагент
            synonym_uk: Контрагент
          - name: Сумма
            type: number
            digits: 15
            fraction_digits: 2
            synonym_ru: Сумма
            synonym_uk: Сума
    commands:
      - name: СформироватьОтчет
        title_ru: Сформировать
        title_uk: Сформувати
        handler: СформироватьОтчет
        shortcut: F5
    elements:
      # Filter section
      - type: UsualGroup
        name: ФильтрыГруппа
        title: Фильтры
        show_title: true
        representation: NormalSeparation
        child_items:
          - type: InputField
            name: ДатаНачалаПоле
            attribute: ДатаНачала
          - type: InputField
            name: ДатаОкончанияПоле
            attribute: ДатаОкончания
          - type: InputField
            name: КонтрагентПоле
            attribute: Контрагент
          - type: Button
            name: СформироватьКнопка
            command: СформироватьОтчет
      # Results table
      - type: Table
        name: РезультатыТаблица
        tabular_section: Результаты
        is_value_table: true
```

**handlers/ПриОткрытии.bsl:**
```bsl
Объект.ДатаНачала = НачалоМесяца(ТекущаяДата());
Объект.ДатаОкончания = КонецМесяца(ТекущаяДата());
```

**handlers/СформироватьОтчет.bsl:**
```bsl
Если НЕ ЗначениеЗаполнено(Объект.ДатаНачала) Тогда
    Сообщить("Укажите дату начала!");
    Возврат;
КонецЕсли;

Если НЕ ЗначениеЗаполнено(Объект.ДатаОкончания) Тогда
    Сообщить("Укажите дату окончания!");
    Возврат;
КонецЕсли;

ЗагрузитьДанныеНаСервере();
```

**handlers/ЗагрузитьДанныеНаСервере.bsl:**
```bsl
Результаты.Clear();

Запрос = Новый Запрос;
Запрос.Текст = "
|SELECT
|    МЕСЯЦ(Документ.Дата) КАК Месяц,
|    Документ.Контрагент.Наименование КАК Контрагент,
|    СУММА(Документ.СуммаДокумента) КАК Сумма
|FROM
|    Документ.РеализацияТоваровУслуг КАК Документ
|WHERE
|    Документ.Дата МЕЖДУ &ДатаНачала И &ДатаОкончания
|    И (&Контрагент = ЗНАЧЕНИЕ(Справочник.Контрагенты.ПустаяСсылка)
|        ИЛИ Документ.Контрагент = &Контрагент)
|СГРУППИРОВАТЬ ПО
|    МЕСЯЦ(Документ.Дата),
|    Документ.Контрагент.Наименование
|";

Запрос.УстановитьПараметр("ДатаНачала", Объект.ДатаНачала);
Запрос.УстановитьПараметр("ДатаОкончания", Объект.ДатаОкончания);
Запрос.УстановитьПараметр("Контрагент", Объект.Контрагент);

РезультатЗапроса = Запрос.Выполнить().Выгрузить();

Для Каждого Строка Из РезультатЗапроса Цикл
    НоваяСтрока = Результаты.Add();
    НоваяСтрока.Месяц = СтрокаМесяца(Строка.Месяц);
    НоваяСтрока.Контрагент = Строка.Контрагент;
    НоваяСтрока.Сумма = Строка.Сумма;
КонецЦикла;

Сообщить("Загружено строк: " + Результаты.Count());
```

---

## Pattern 3: Multi-Step Wizard

**Use case:** Sequential process with steps

**Structure:** Pages (tabs) with navigation

```yaml
processor:
  name: МастерИмпорта
  synonym_ru: Мастер импорта
  synonym_uk: Майстер імпорту

attributes:
  - name: ПутьКФайлу
    type: string
    length: 500
    synonym_ru: Путь к файлу

  - name: Кодировка
    type: string
    length: 50
    synonym_ru: Кодировка

forms:
  - name: Форма
    default: true
    properties:
      title: true
      title_ru: Мастер импорта данных
      title_uk: Майстер імпорту даних
    value_tables:
      - name: Предпросмотр
        columns:
          - name: Строка
            type: string
            length: 500
    commands:
      - name: ВыбратьФайл
        title_ru: Выбрать файл
        title_uk: Вибрати файл
        handler: ВыбратьФайл
      - name: Далее1
        title_ru: Далее
        title_uk: Далі
        handler: Далее1
      - name: Назад2
        title_ru: Назад
        title_uk: Назад
        handler: Назад2
      - name: Далее2
        title_ru: Далее
        title_uk: Далі
        handler: Далее2
      - name: ИмпортироватьДанные
        title_ru: Импорт
        title_uk: Імпорт
        handler: ИмпортироватьДанные
      - name: ЗакрытьФорму
        title_ru: Закрыть
        title_uk: Закрити
        handler: ЗакрытьФорму
    elements:
      - type: Pages
        name: Шаги
        pages_representation: TabsOnTop
        pages:
          # Step 1: File selection
          - name: Шаг1
            title: Шаг 1: Выбор файла
            child_items:
              - type: LabelDecoration
                name: Инструкция1
                title: Выберите файл для импорта
              - type: InputField
                name: ПутьКФайлуПоле
                attribute: ПутьКФайлу
              - type: Button
                name: ВыбратьФайлКнопка
                command: ВыбратьФайл
              - type: UsualGroup
                name: Навигация1
                group_direction: Horizontal
                child_items:
                  - type: Button
                    name: Далее1Кнопка
                    command: Далее1
          # Step 2: Preview
          - name: Шаг2
            title: Шаг 2: Предпросмотр
            child_items:
              - type: LabelDecoration
                name: Инструкция2
                title: Проверьте данные перед импортом
              - type: Table
                name: ПредпросмотрТаблица
                tabular_section: Предпросмотр
                is_value_table: true
              - type: UsualGroup
                name: Навигация2
                group_direction: Horizontal
                child_items:
                  - type: Button
                    name: Назад2Кнопка
                    command: Назад2
                  - type: Button
                    name: Далее2Кнопка
                    command: Далее2
          # Step 3: Import
          - name: Шаг3
            title: Шаг 3: Импорт
            child_items:
              - type: LabelDecoration
                name: Инструкция3
                title: Нажмите кнопку для начала импорта
              - type: Button
                name: ИмпортКнопка
                command: ИмпортироватьДанные
              - type: Button
                name: ЗакрытьКнопка
                command: ЗакрытьФорму
```

**handlers/ВыбратьФайл.bsl:**
```bsl
Диалог = Новый ДиалогВыбораФайла(РежимДиалогаВыбораФайла.Открытие);
Диалог.Фильтр = "Текстовые файлы (*.txt)|*.txt|Все файлы (*.*)|*.*";
Диалог.Заголовок = "Выберите файл";

Если Диалог.Выбрать() Тогда
    Объект.ПутьКФайлу = Диалог.ПолноеИмяФайла;
    Сообщить("Выбран файл: " + Объект.ПутьКФайлу);
КонецЕсли;
```

**handlers/Далее1.bsl:**
```bsl
Если НЕ ЗначениеЗаполнено(Объект.ПутьКФайлу) Тогда
    Сообщить("Выберите файл!");
    Возврат;
КонецЕсли;

ЗагрузитьПредпросмотрНаСервере();
Items.Шаги.CurrentPage = Items.Шаг2;
```

---

## Pattern 4: Master-Detail

**Use case:** Table with selected row details

**Structure:** Table → Details panel with CurrentData

```yaml
processor:
  name: ПросмотрТоваров
  synonym_ru: Просмотр товаров
  synonym_uk: Перегляд товарів

forms:
  - name: Форма
    default: true
    events:
      OnOpen: ПриОткрытии
    value_tables:
      - name: Товары
        columns:
          - name: Код
            type: string
            length: 50
          - name: Наименование
            type: string
            length: 200
          - name: Цена
            type: number
            digits: 15
            fraction_digits: 2
          - name: Остаток
            type: number
            digits: 10
            fraction_digits: 2
    elements:
      # Master: Table
      - type: Table
        name: ТоварыТаблица
        tabular_section: Товары
        is_value_table: true
      # Detail: Selected row info
      - type: UsualGroup
        name: ДетальнаяИнформация
        title: Детальная информация
        show_title: true
        representation: NormalSeparation
        child_items:
          - type: LabelField
            name: ВыбранКодМетка
            data_path: Items.ТоварыТаблица.CurrentData.Код
          - type: LabelField
            name: ВыбранНаименованиеМетка
            data_path: Items.ТоварыТаблица.CurrentData.Наименование
          - type: LabelField
            name: ВыбранЦенаМетка
            data_path: Items.ТоварыТаблица.CurrentData.Цена
          - type: LabelField
            name: ВыбранОстатокМетка
            data_path: Items.ТоварыТаблица.CurrentData.Остаток
```

**handlers/ПриОткрытии.bsl:**
```bsl
ЗагрузитьТоварыНаСервере();
```

**handlers/ЗагрузитьТоварыНаСервере.bsl:**
```bsl
Товары.Clear();

Запрос = Новый Запрос;
Запрос.Текст = "
|SELECT TOP 100
|    Номенклатура.Код,
|    Номенклатура.Наименование,
|    Номенклатура.Цена,
|    ЕСТЬNULL(Остатки.Количество, 0) КАК Остаток
|FROM
|    Справочник.Номенклатура КАК Номенклатура
|LEFT JOIN
|    РегистрНакопления.ОстаткиНоменклатуры.Остатки КАК Остатки
|    ПО Номенклатура.Ссылка = Остатки.Номенклатура
|";

РезультатЗапроса = Запрос.Выполнить().Выгрузить();

Для Каждого Строка Из РезультатЗапроса Цикл
    НоваяСтрока = Товары.Add();
    ЗаполнитьЗначенияСвойств(НоваяСтрока, Строка);
КонецЦикла;
```

---

## Pattern 5: CRUD (Create, Read, Update, Delete)

**Use case:** Manage data with full CRUD operations

**Structure:** Table → Edit form → Action buttons

```yaml
processor:
  name: УправлениеЗаписями
  synonym_ru: Управление записями
  synonym_uk: Керування записами

attributes:
  - name: ТекущийID
    type: string
    length: 36
  - name: ТекущееНаименование
    type: string
    length: 200
  - name: ТекущийКомментарий
    type: string
    length: 500

forms:
  - name: Форма
    default: true
    events:
      OnOpen: ПриОткрытии
    value_tables:
      - name: Записи
        columns:
          - name: ID
            type: string
            length: 36
          - name: Наименование
            type: string
            length: 200
          - name: Комментарий
            type: string
            length: 500
    commands:
      - name: ДобавитьЗапись
        title_ru: Добавить
        title_uk: Додати
        handler: ДобавитьЗапись
      - name: ИзменитьЗапись
        title_ru: Изменить
        title_uk: Змінити
        handler: ИзменитьЗапись
      - name: УдалитьЗапись
        title_ru: Удалить
        title_uk: Видалити
        handler: УдалитьЗапись
      - name: ОчиститьДанные
        title_ru: Очистить
        title_uk: Очистити
        handler: ОчиститьДанные
    elements:
      # Table
      - type: Table
        name: ЗаписиТаблица
        tabular_section: Записи
        is_value_table: true
      # Edit form
      - type: UsualGroup
        name: РедактированиеГруппа
        title: Редактирование
        show_title: true
        child_items:
          - type: InputField
            name: ТекущееНаименованиеПоле
            attribute: ТекущееНаименование
          - type: InputField
            name: ТекущийКомментарийПоле
            attribute: ТекущийКомментарий
      # Actions
      - type: UsualGroup
        name: ДействияГруппа
        group_direction: Horizontal
        child_items:
          - type: Button
            name: ДобавитьКнопка
            command: ДобавитьЗапись
          - type: Button
            name: ИзменитьКнопка
            command: ИзменитьЗапись
          - type: Button
            name: УдалитьКнопка
            command: УдалитьЗапись
          - type: Button
            name: ОчиститьКнопка
            command: ОчиститьДанные
```

**handlers/ДобавитьЗапись.bsl:**
```bsl
Если НЕ ЗначениеЗаполнено(Объект.ТекущееНаименование) Тогда
    Сообщить("Заполните наименование!");
    Возврат;
КонецЕсли;

НоваяСтрока = Записи.Add();
НоваяСтрока.ID = Строка(Новый УникальныйИдентификатор);
НоваяСтрока.Наименование = Объект.ТекущееНаименование;
НоваяСтрока.Комментарий = Объект.ТекущийКомментарий;

Объект.ТекущееНаименование = "";
Объект.ТекущийКомментарий = "";

Сообщить("Запись добавлена");
```

**handlers/УдалитьЗапись.bsl:**
```bsl
ТекущаяСтрока = Items.ЗаписиТаблица.CurrentData;

Если ТекущаяСтрока = Неопределено Тогда
    Сообщить("Выберите строку для удаления!");
    Возврат;
КонецЕсли;

Записи.Delete(Записи.IndexOf(ТекущаяСтрока));
Сообщить("Запись удалена");
```

---

## Best Practices

1. **Group related fields** - Use `UsualGroup` with title
2. **Action buttons horizontal** - At top or bottom of form
3. **Tables should be prominent** - Give them space
4. **Wizards for 3+ steps** - Use `Pages` with clear titles
5. **Validate early** - Check data before server calls
6. **CurrentData for details** - Display selected row info
7. **Clear instructions** - Use `LabelDecoration` for guidance

---

**Version:** 2.38.0 (2025-11-26)
