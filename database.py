from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    Float,
    DateTime,
    Boolean,
    ForeignKey
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relationship

Base = declarative_base()

class LegalAddress(Base):
    __tablename__ = 'юридический_адрес'

    id = Column(Integer, primary_key=True)
    Индекс = Column(Integer)
    Регион = Column(String)
    Город = Column(String)
    Улица = Column(String)
    Дом = Column(Integer)

    склады = relationship("Warehouse", back_populates="юридический_адрес")
    партнеры = relationship("Partner", back_populates="юридический_адрес")


class WarehouseType(Base):
    __tablename__ = 'тип_склада'

    id = Column(Integer, primary_key=True)
    Наименование = Column(String)

    склады = relationship("Warehouse", back_populates="тип")


class Warehouse(Base):
    __tablename__ = 'склад'

    id = Column(Integer, primary_key=True)
    Название = Column(String(50))
    id_тип = Column(Integer, ForeignKey('тип_склада.id'))
    Описание = Column(String(255))
    id_юр_адрес = Column(Integer, ForeignKey('юридический_адрес.id'))

    тип = relationship("WarehouseType", back_populates="склады")
    юридический_адрес = relationship("LegalAddress", back_populates="склады")
    поступления_товаров = relationship("IncomingInvoice", back_populates="склад")
    перемещения_откуда = relationship("ProductMovement", foreign_keys="[ProductMovement.id_склад_откуда]",
                                       back_populates="склад_откуда")
    перемещения_куда = relationship("ProductMovement", foreign_keys="[ProductMovement.id_склад_куда]",
                                     back_populates="склад_куда")

    продукция_на_складе = relationship("ProductOnWarehouse", back_populates="склад")


class ProductType(Base):
    __tablename__ = 'тип_продукции'

    id = Column(Integer, primary_key=True)
    Наименование = Column(String)

    продукции = relationship("Product", back_populates="тип")
    
    группа_тип_продукции = relationship("GroupProductType", back_populates="тип_продукции")
    
class ProductGroup(Base):
    __tablename__ = 'группа_продукции'

    id = Column(Integer, primary_key=True)
    Наименование = Column(String)
    Изображение = Column(String)
    
    группа_тип_продукции = relationship("GroupProductType", back_populates="группа_продукции")
    
class GroupProductType(Base):
    __tablename__ = 'группа_тип_продукции'

    id = Column(Integer, primary_key=True)
    id_тип_продукции = Column(Integer, ForeignKey('тип_продукции.id'))
    id_группа_продукции = Column(Integer, ForeignKey('группа_продукции.id'))

    тип_продукции = relationship("ProductType", back_populates="группа_тип_продукции")
    группа_продукции = relationship("ProductGroup", back_populates="группа_тип_продукции")


class Product(Base):
    __tablename__ = 'продукция'

    id = Column(Integer, primary_key=True)
    id_тип = Column(Integer, ForeignKey('тип_продукции.id'))
    Наименование = Column(String)
    Описание = Column(String)
    Стоимость = Column(Float)
    Размер_упаковки = Column(String)
    Вес = Column(String)
    Изображение = Column(String)  
    

    тип = relationship("ProductType", back_populates="продукции")
    поступления_товаров = relationship("IncomingInvoice", back_populates="продукция")
    перемещения = relationship("ProductMovement", back_populates="продукция")

    продукция_на_складе = relationship("ProductOnWarehouse", back_populates="продукция")
    заказы_продукции = relationship("OrderProduct", back_populates="продукция")


class Passport(Base):
    __tablename__ = 'паспорт'

    id = Column(Integer, primary_key=True)
    Серия = Column(Integer)
    Номер = Column(Integer)
    Кем_выдан = Column(String)
    Дата_выдачи = Column(Date)

    сотрудники = relationship("Employee", back_populates="паспорт")


class BankDetails(Base):
    __tablename__ = 'банковские_реквизиты'

    id = Column(Integer, primary_key=True)
    Название_организации = Column(String)
    Название_банка = Column(String)
    ИНН = Column(Integer)
    БИК = Column(Integer)
    Корреспондентский_счет = Column(String)

    сотрудники = relationship("Employee", back_populates="банковские_реквизиты")


class Position(Base):
    __tablename__ = 'должность'

    id = Column(Integer, primary_key=True)
    Наименование = Column(String)

    сотрудники = relationship("Employee", back_populates="должность")


class Employee(Base):
    __tablename__ = 'сотрудник'

    id = Column(Integer, primary_key=True)
    Фамилия = Column(String)
    Имя = Column(String)
    Отчество = Column(String)
    Дата_рождения = Column(Date)
    id_паспорт = Column(Integer, ForeignKey('паспорт.id'))
    id_банк_реквизиты = Column(Integer, ForeignKey('банковские_реквизиты.id'))
    id_должность = Column(Integer, ForeignKey('должность.id'))
    Логин = Column(String, unique=True)
    Пароль = Column(String)

    паспорт = relationship("Passport", back_populates="сотрудники")
    банковские_реквизиты = relationship("BankDetails", back_populates="сотрудники")
    должность = relationship("Position", back_populates="сотрудники")
    перемещения = relationship("ProductMovement", back_populates="сотрудник")
    заказы = relationship("Order", back_populates="сотрудник")


class IncomingInvoice(Base):
    __tablename__ = 'поступление_товара'

    id = Column(Integer, primary_key=True)
    id_продукция = Column(Integer, ForeignKey('продукция.id'))
    id_склад = Column(Integer, ForeignKey('склад.id'))
    Дата_поступления = Column(DateTime)
    Кол_во_товара = Column(Integer)

    продукция = relationship("Product", back_populates="поступления_товаров")
    склад = relationship("Warehouse", back_populates="поступления_товаров")


class ProductMovement(Base):
    __tablename__ = 'перемещение_продукции'

    id = Column(Integer, primary_key=True)
    id_продукции = Column(Integer, ForeignKey('продукция.id'))
    id_склад_откуда = Column(Integer, ForeignKey('склад.id'))
    id_склад_куда = Column(Integer, ForeignKey('склад.id'))
    Количество = Column(Integer)
    Дата_перемещения = Column(DateTime)
    Статус = Column(String)
    id_сотрудник = Column(Integer, ForeignKey('сотрудник.id'))

    продукция = relationship("Product", back_populates="перемещения")
    склад_откуда = relationship("Warehouse", foreign_keys=[id_склад_откуда], back_populates="перемещения_откуда")
    склад_куда = relationship("Warehouse", foreign_keys=[id_склад_куда], back_populates="перемещения_куда")
    сотрудник = relationship("Employee", back_populates="перемещения")


class ProductOnWarehouse(Base):
    __tablename__ = 'продукция_на_складе'

    id = Column(Integer, primary_key=True)
    id_склада = Column(Integer, ForeignKey('склад.id'))
    id_продукции = Column(Integer, ForeignKey('продукция.id'))
    Количество = Column(Integer)

    продукция = relationship("Product", back_populates="продукция_на_складе")
    склад = relationship("Warehouse", back_populates="продукция_на_складе")


class PartnerType(Base):
    __tablename__ = 'тип_партнера'

    id = Column(Integer, primary_key=True)
    Наименование = Column(String)

    партнеры = relationship("Partner", back_populates="тип")

class Partner(Base):
    __tablename__ = 'партнер'

    id = Column(Integer, primary_key=True)
    id_юр_адрес = Column(Integer, ForeignKey('юридический_адрес.id'))
    Наименование = Column(String)
    ИНН = Column(String)  # Изменено на String
    ФИО_директора = Column(String)
    id_тип = Column(Integer, ForeignKey('тип_партнера.id'))
    Телефон = Column(String)  # Изменено на String
    email = Column(String)
    Места_продаж = Column(String)
    Пароль = Column(String)
    
    юридический_адрес = relationship("LegalAddress", back_populates="партнеры")
    тип = relationship("PartnerType", back_populates="партнеры")
    заказы = relationship("Order", back_populates="партнер")

class Order(Base):
    __tablename__ = 'заказ'

    id = Column(Integer, primary_key=True)
    Дата_создания = Column(Date)
    Статус = Column(String)
    id_сотрудник = Column(Integer, ForeignKey('сотрудник.id'))
    id_партнер = Column(Integer, ForeignKey('партнер.id'))
    Предоплата = Column(Float)
    Согласована = Column(Boolean)

    сотрудник = relationship("Employee", back_populates="заказы")
    партнер = relationship("Partner", back_populates="заказы")
    заказы_продукции = relationship("OrderProduct", back_populates="заказ")


class OrderProduct(Base):
    __tablename__ = 'заказ_продукции'

    id = Column(Integer, primary_key=True)
    id_заказа = Column(Integer, ForeignKey('заказ.id'))
    id_продукции = Column(Integer, ForeignKey('продукция.id'))
    Количество = Column(Integer)
    Стоимость = Column(Float)

    заказ = relationship("Order", back_populates="заказы_продукции")
    продукция = relationship("Product", back_populates="заказы_продукции")

class Connect:
    @staticmethod
    def create_connection():
        engine = create_engine("postgresql://postgres:1234@localhost:5432/coursework")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        return session