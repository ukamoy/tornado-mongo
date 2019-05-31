from handlers import dashboard, users, deploy,mainipulator

handlers=[]
handlers.extend(dashboard.handlers)
handlers.extend(users.handlers)
handlers.extend(deploy.handlers)
handlers.extend(mainipulator.handlers)