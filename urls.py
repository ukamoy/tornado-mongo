from handlers import dashboard, users, deploy,manipulator

handlers=[]
handlers.extend(dashboard.handlers)
handlers.extend(users.handlers)
handlers.extend(deploy.handlers)
handlers.extend(manipulator.handlers)