from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from bot.models.expense import Expense

async def add_expense(session: AsyncSession, user_id: int, amount: int, purpose: str, source: str):
    expense = Expense(user_id=user_id, amount=amount, purpose=purpose, source=source)
    session.add(expense)
    await session.commit()

async def get_expenses(session: AsyncSession, user_id: int):
    result = await session.execute(select(Expense).where(Expense.user_id == user_id, Expense.source == "собственные средства"))
    return result.scalars().all()

async def update_expense(session: AsyncSession, expense_id: int, amount: int, purpose: str):
    expense = await session.get(Expense, expense_id)
    if expense:
        expense.amount = amount
        expense.purpose = purpose
        await session.commit()

async def change_expense_source(session: AsyncSession, expense_id: int):
    expense = await session.get(Expense, expense_id)
    if expense:
        expense.source = "касса"
        await session.commit()

async def delete_expense(session: AsyncSession, expense_id: int):
    expense = await session.get(Expense, expense_id)
    if expense:
        await session.delete(expense)
        await session.commit()
