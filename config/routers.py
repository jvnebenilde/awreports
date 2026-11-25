class NoMigrateAdventureWorks:
    """Django must never create or alter tables in AdventureWorks."""
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return db == "default"
