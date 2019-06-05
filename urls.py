from handlers import dashboard, users, deploy,operator

handlers=[]
handlers.extend(dashboard.handlers)
handlers.extend(users.handlers)
handlers.extend(deploy.handlers)
handlers.extend(operator.handlers)