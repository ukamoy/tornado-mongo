from handlers import dashboard, users, panel,operator

handlers=[]
handlers.extend(dashboard.handlers)
handlers.extend(users.handlers)
handlers.extend(panel.handlers)
handlers.extend(operator.handlers)