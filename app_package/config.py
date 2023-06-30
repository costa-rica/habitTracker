import os
from ht_config import ConfigLocal, ConfigDev, ConfigProd

match os.environ.get('FLASK_ENV'):
    case 'dev':
        config = ConfigDev()
        print('- exFlaskBlueprintFrameworkStarterWithLogin/app_pacakge/config: Development')
    case 'prod':
        config = ConfigProd()
        print('- exFlaskBlueprintFrameworkStarterWithLogin/app_pacakge/config: Production')
    case _:
        config = ConfigLocal()
        print('- exFlaskBlueprintFrameworkStarterWithLogin/app_pacakge/config: Local')