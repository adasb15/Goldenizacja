IF DB_ID(N'goldenizacja') IS NULL
BEGIN
    CREATE DATABASE [goldenizacja];
END;
GO

USE [goldenizacja];
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'meta')
    EXEC(N'CREATE SCHEMA [meta]');
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'raw')
    EXEC(N'CREATE SCHEMA [raw]');
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'stg')
    EXEC(N'CREATE SCHEMA [stg]');
GO

IF OBJECT_ID(N'[meta].[SourceSystem]', N'U') IS NULL
BEGIN
    CREATE TABLE [meta].[SourceSystem] (
        [SourceSystem_ID] INT IDENTITY(1,1) NOT NULL,
        [SourceSystem_Code] NVARCHAR(50) NOT NULL,
        [SourceSystem_Name] NVARCHAR(255) NOT NULL,
        [Trust_Level] TINYINT NULL,
        [Created_At] DATETIME2(0) NOT NULL CONSTRAINT [DF_SourceSystem_Created_At] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [PK_SourceSystem] PRIMARY KEY CLUSTERED ([SourceSystem_ID]),
        CONSTRAINT [UQ_SourceSystem_Code] UNIQUE ([SourceSystem_Code]),
        CONSTRAINT [CK_SourceSystem_Trust_Level] CHECK ([Trust_Level] IS NULL OR [Trust_Level] BETWEEN 0 AND 100)
    );
END;
GO

IF OBJECT_ID(N'[meta].[ImportBatch]', N'U') IS NULL
BEGIN
    CREATE TABLE [meta].[ImportBatch] (
        [ImportBatch_ID] BIGINT IDENTITY(1,1) NOT NULL,
        [SourceSystem_ID] INT NOT NULL,
        [Import_Status] NVARCHAR(30) NOT NULL,
        [Import_Start_At] DATETIME2(0) NOT NULL CONSTRAINT [DF_ImportBatch_Start_At] DEFAULT SYSUTCDATETIME(),
        [Import_End_At] DATETIME2(0) NULL,
        [Created_By] NVARCHAR(100) NULL,
        [Error_Message] NVARCHAR(MAX) NULL,
        [Created_At] DATETIME2(0) NOT NULL CONSTRAINT [DF_ImportBatch_Created_At] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [PK_ImportBatch] PRIMARY KEY CLUSTERED ([ImportBatch_ID]),
        CONSTRAINT [FK_ImportBatch_SourceSystem] FOREIGN KEY ([SourceSystem_ID])
            REFERENCES [meta].[SourceSystem] ([SourceSystem_ID]),
        CONSTRAINT [CK_ImportBatch_Status] CHECK ([Import_Status] IN (
            N'NEW', N'PROCESSING', N'RAW_LOADED', N'STAGING_LOADED', N'COMPLETED', N'FAILED'
        ))
    );
END;
GO

IF OBJECT_ID(N'[meta].[ColumnMapping]', N'U') IS NULL
BEGIN
    CREATE TABLE [meta].[ColumnMapping] (
        [ColumnMapping_ID] INT IDENTITY(1,1) NOT NULL,
        [SourceSystem_ID] INT NOT NULL,
        [Entity_Type] NVARCHAR(20) NOT NULL,
        [Source_Column_Name] NVARCHAR(255) NOT NULL,
        [Canonical_Column_Name] NVARCHAR(255) NOT NULL,
        [Created_At] DATETIME2(0) NOT NULL CONSTRAINT [DF_ColumnMapping_Created_At] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [PK_ColumnMapping] PRIMARY KEY CLUSTERED ([ColumnMapping_ID]),
        CONSTRAINT [FK_ColumnMapping_SourceSystem] FOREIGN KEY ([SourceSystem_ID])
            REFERENCES [meta].[SourceSystem] ([SourceSystem_ID]),
        CONSTRAINT [UQ_ColumnMapping_Source_Entity_Column] UNIQUE (
            [SourceSystem_ID], [Entity_Type], [Source_Column_Name]
        ),
        CONSTRAINT [CK_ColumnMapping_Entity_Type] CHECK ([Entity_Type] IN (N'PERSON', N'PARTY'))
    );
END;
GO

IF OBJECT_ID(N'[raw].[RawFile]', N'U') IS NULL
BEGIN
    CREATE TABLE [raw].[RawFile] (
        [RawFile_ID] BIGINT IDENTITY(1,1) NOT NULL,
        [ImportBatch_ID] BIGINT NOT NULL,
        [File_Name] NVARCHAR(260) NOT NULL,
        [File_Type] NVARCHAR(30) NOT NULL,
        [File_Size] BIGINT NOT NULL,
        [File_Hash] CHAR(64) NOT NULL,
        [File_Content] VARBINARY(MAX) NULL,
        [Created_At] DATETIME2(0) NOT NULL CONSTRAINT [DF_RawFile_Created_At] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [PK_RawFile] PRIMARY KEY CLUSTERED ([RawFile_ID]),
        CONSTRAINT [FK_RawFile_ImportBatch] FOREIGN KEY ([ImportBatch_ID])
            REFERENCES [meta].[ImportBatch] ([ImportBatch_ID]),
        CONSTRAINT [UQ_RawFile_File_Hash] UNIQUE ([File_Hash]),
        CONSTRAINT [CK_RawFile_File_Size] CHECK ([File_Size] >= 0)
    );
END;
GO

IF OBJECT_ID(N'[meta].[ProcessLog]', N'U') IS NULL
BEGIN
    CREATE TABLE [meta].[ProcessLog] (
        [ProcessLog_ID] BIGINT IDENTITY(1,1) NOT NULL,
        [ImportBatch_ID] BIGINT NOT NULL,
        [RawFile_ID] BIGINT NULL,
        [Staging_ID] BIGINT NULL,
        [Step_Name] NVARCHAR(50) NOT NULL,
        [Step_Status] NVARCHAR(30) NOT NULL,
        [Started_At] DATETIME2(0) NOT NULL CONSTRAINT [DF_ProcessLog_Started_At] DEFAULT SYSUTCDATETIME(),
        [Ended_At] DATETIME2(0) NULL,
        [Records_In] BIGINT NULL,
        [Records_Out] BIGINT NULL,
        [Error_Message] NVARCHAR(MAX) NULL,
        [Created_At] DATETIME2(0) NOT NULL CONSTRAINT [DF_ProcessLog_Created_At] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [PK_ProcessLog] PRIMARY KEY CLUSTERED ([ProcessLog_ID]),
        CONSTRAINT [FK_ProcessLog_ImportBatch] FOREIGN KEY ([ImportBatch_ID])
            REFERENCES [meta].[ImportBatch] ([ImportBatch_ID]),
        CONSTRAINT [FK_ProcessLog_RawFile] FOREIGN KEY ([RawFile_ID])
            REFERENCES [raw].[RawFile] ([RawFile_ID]),
        CONSTRAINT [CK_ProcessLog_Step_Name] CHECK ([Step_Name] IN (
            N'RAW_LOAD', N'STAGING_LOAD', N'STANDARDIZATION', N'VALIDATION'
        )),
        CONSTRAINT [CK_ProcessLog_Step_Status] CHECK ([Step_Status] IN (
            N'STARTED', N'SUCCESS', N'FAILED'
        ))
    );
END;
GO

IF EXISTS (
    SELECT 1
    FROM sys.check_constraints
    WHERE [name] = N'CK_ProcessLog_Step_Name'
    AND parent_object_id = OBJECT_ID(N'meta.ProcessLog')
)
BEGIN
    ALTER TABLE [meta].[ProcessLog] DROP CONSTRAINT [CK_ProcessLog_Step_Name];
    ALTER TABLE [meta].[ProcessLog] ADD CONSTRAINT [CK_ProcessLog_Step_Name] CHECK ([Step_Name] IN (
        N'RAW_LOAD', N'STAGING_LOAD', N'STANDARDIZATION', N'VALIDATION'
    ));
END;
GO

IF OBJECT_ID(N'[stg].[Person_Staging]', N'U') IS NULL
BEGIN
    CREATE TABLE [stg].[Person_Staging] (
        [Staging_ID] BIGINT IDENTITY(1,1) NOT NULL,
        [ImportBatch_ID] BIGINT NOT NULL,
        [RawFile_ID] BIGINT NOT NULL,
        [Source_Record_ID] NVARCHAR(100) NULL,
        [PESEL] NVARCHAR(11) NULL,
        [Serial_Number_ID_Card] NVARCHAR(30) NULL,
        [Serial_Number_Passport] NVARCHAR(30) NULL,
        [First_Name] NVARCHAR(100) NULL,
        [Second_Name] NVARCHAR(100) NULL,
        [Last_Name] NVARCHAR(100) NULL,
        [Family_Name] NVARCHAR(100) NULL,
        [Birth_Date] DATE NULL,
        [Place_Of_Birth] NVARCHAR(150) NULL,
        [Sex] BIT NULL,
        [Citizenship] NVARCHAR(100) NULL,
        [Phone_Number] NVARCHAR(50) NULL,
        [Email_Address] NVARCHAR(255) NULL,
        [Street] NVARCHAR(150) NULL,
        [Building_Number] NVARCHAR(30) NULL,
        [Apartment_Number] NVARCHAR(30) NULL,
        [City] NVARCHAR(100) NULL,
        [Postal_City] NVARCHAR(100) NULL,
        [Postal_Code] NVARCHAR(20) NULL,
        [District] NVARCHAR(100) NULL,
        [Province] NVARCHAR(100) NULL,
        [Country] NVARCHAR(100) NULL,
        [Raw_Record_JSON] NVARCHAR(MAX) NULL,
        [Created_At] DATETIME2(0) NOT NULL CONSTRAINT [DF_Person_Staging_Created_At] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [PK_Person_Staging] PRIMARY KEY CLUSTERED ([Staging_ID]),
        CONSTRAINT [FK_Person_Staging_ImportBatch] FOREIGN KEY ([ImportBatch_ID])
            REFERENCES [meta].[ImportBatch] ([ImportBatch_ID]),
        CONSTRAINT [FK_Person_Staging_RawFile] FOREIGN KEY ([RawFile_ID])
            REFERENCES [raw].[RawFile] ([RawFile_ID]),
        CONSTRAINT [CK_Person_Staging_Raw_JSON] CHECK ([Raw_Record_JSON] IS NULL OR ISJSON([Raw_Record_JSON]) = 1)
    );
END;
GO

IF OBJECT_ID(N'[stg].[Person_Staging]', N'U') IS NOT NULL
AND EXISTS (
    SELECT 1
    FROM sys.check_constraints
    WHERE [name] = N'CK_Person_Staging_Sex'
    AND parent_object_id = OBJECT_ID(N'stg.Person_Staging')
)
    ALTER TABLE [stg].[Person_Staging] DROP CONSTRAINT [CK_Person_Staging_Sex];

IF COL_LENGTH(N'stg.Person_Staging', N'Sex') IS NOT NULL
AND TYPE_NAME(COLUMNPROPERTY(OBJECT_ID(N'stg.Person_Staging'), N'Sex', 'SystemTypeId')) <> N'bit'
BEGIN
    UPDATE [stg].[Person_Staging]
    SET [Sex] = CASE
        WHEN [Sex] IN (N'K', N'k', N'1') THEN N'1'
        WHEN [Sex] IN (N'M', N'm', N'0') THEN N'0'
        ELSE NULL
    END;

    ALTER TABLE [stg].[Person_Staging] ALTER COLUMN [Sex] BIT NULL;
END;

IF OBJECT_ID(N'[stg].[Party_Staging]', N'U') IS NULL
BEGIN
    CREATE TABLE [stg].[Party_Staging] (
        [Staging_ID] BIGINT IDENTITY(1,1) NOT NULL,
        [ImportBatch_ID] BIGINT NOT NULL,
        [RawFile_ID] BIGINT NOT NULL,
        [Source_Record_ID] NVARCHAR(100) NULL,
        [Name] NVARCHAR(255) NULL,
        [Short_Name] NVARCHAR(255) NULL,
        [Legal_Entity_Type] NVARCHAR(100) NULL,
        [Registration_Country] NVARCHAR(100) NULL,
        [Establishment_Date] DATE NULL,
        [Identifiers_JSON] NVARCHAR(MAX) NULL,
        [Street] NVARCHAR(150) NULL,
        [Building_Number] NVARCHAR(30) NULL,
        [Apartment_Number] NVARCHAR(30) NULL,
        [City] NVARCHAR(100) NULL,
        [Postal_City] NVARCHAR(100) NULL,
        [Postal_Code] NVARCHAR(20) NULL,
        [District] NVARCHAR(100) NULL,
        [Province] NVARCHAR(100) NULL,
        [Country] NVARCHAR(100) NULL,
        [Register_Status] NVARCHAR(100) NULL,
        [Registration_Date] DATE NULL,
        [Deregistration_Date] DATE NULL,
        [Decision_Date] DATE NULL,
        [Decision_Number] NVARCHAR(100) NULL,
        [Register_Number] NVARCHAR(100) NULL,
        [Bank_Accounts_JSON] NVARCHAR(MAX) NULL,
        [Has_Virtual_Accounts] BIT NULL,
        [Business_Scope] NVARCHAR(MAX) NULL,
        [Ownership_Form] NVARCHAR(150) NULL,
        [Municipality] NVARCHAR(100) NULL,
        [Phone_Number] NVARCHAR(50) NULL,
        [Email_Address] NVARCHAR(255) NULL,
        [Website] NVARCHAR(255) NULL,
        [Agent_Type] NVARCHAR(100) NULL,
        [Insurance_Company] NVARCHAR(255) NULL,
        [Related_Persons_JSON] NVARCHAR(MAX) NULL,
        [Related_Parties_JSON] NVARCHAR(MAX) NULL,
        [Registration_Status] NVARCHAR(50) NULL,
        [Last_Update_Date] DATE NULL,
        [Next_Renewal_Date] DATE NULL,
        [Managing_LOU] NVARCHAR(50) NULL,
        [Validation_Sources] NVARCHAR(100) NULL,
        [Validation_Authority_ID] NVARCHAR(500) NULL,
        [Validation_Authority_Entity_ID] NVARCHAR(100) NULL,
        [Direct_Parent_LEI] NVARCHAR(20) NULL,
        [Direct_Parent_Name] NVARCHAR(255) NULL,
        [Direct_Parent_Relationship_Type] NVARCHAR(100) NULL,
        [Direct_Parent_Relationship_Status] NVARCHAR(50) NULL,
        [Direct_Parent_Relationship_Start_Date] DATE NULL,
        [Direct_Parent_Relationship_End_Date] DATE NULL,
        [Ultimate_Parent_LEI] NVARCHAR(20) NULL,
        [Ultimate_Parent_Name] NVARCHAR(255) NULL,
        [Ultimate_Parent_Relationship_Type] NVARCHAR(100) NULL,
        [Ultimate_Parent_Relationship_Status] NVARCHAR(50) NULL,
        [Ultimate_Parent_Relationship_Start_Date] DATE NULL,
        [Ultimate_Parent_Relationship_End_Date] DATE NULL,
        [Raw_Record_JSON] NVARCHAR(MAX) NULL,
        [Created_At] DATETIME2(0) NOT NULL CONSTRAINT [DF_Party_Staging_Created_At] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [PK_Party_Staging] PRIMARY KEY CLUSTERED ([Staging_ID]),
        CONSTRAINT [FK_Party_Staging_ImportBatch] FOREIGN KEY ([ImportBatch_ID])
            REFERENCES [meta].[ImportBatch] ([ImportBatch_ID]),
        CONSTRAINT [FK_Party_Staging_RawFile] FOREIGN KEY ([RawFile_ID])
            REFERENCES [raw].[RawFile] ([RawFile_ID]),
        CONSTRAINT [CK_Party_Staging_Identifiers_JSON] CHECK ([Identifiers_JSON] IS NULL OR ISJSON([Identifiers_JSON]) = 1),
        CONSTRAINT [CK_Party_Staging_Bank_Accounts_JSON] CHECK ([Bank_Accounts_JSON] IS NULL OR ISJSON([Bank_Accounts_JSON]) = 1),
        CONSTRAINT [CK_Party_Staging_Related_Persons_JSON] CHECK ([Related_Persons_JSON] IS NULL OR ISJSON([Related_Persons_JSON]) = 1),
        CONSTRAINT [CK_Party_Staging_Related_Parties_JSON] CHECK ([Related_Parties_JSON] IS NULL OR ISJSON([Related_Parties_JSON]) = 1),
        CONSTRAINT [CK_Party_Staging_Raw_JSON] CHECK ([Raw_Record_JSON] IS NULL OR ISJSON([Raw_Record_JSON]) = 1)
    );
END;
GO

IF COL_LENGTH(N'stg.Party_Staging', N'Registration_Status') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Registration_Status] NVARCHAR(50) NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Register_Status') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Register_Status] NVARCHAR(100) NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Registration_Date') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Registration_Date] DATE NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Deregistration_Date') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Deregistration_Date] DATE NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Decision_Date') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Decision_Date] DATE NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Decision_Number') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Decision_Number] NVARCHAR(100) NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Register_Number') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Register_Number] NVARCHAR(100) NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Bank_Accounts_JSON') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Bank_Accounts_JSON] NVARCHAR(MAX) NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Has_Virtual_Accounts') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Has_Virtual_Accounts] BIT NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Has_Virtual_Accounts') IS NOT NULL
AND TYPE_NAME(COLUMNPROPERTY(OBJECT_ID(N'stg.Party_Staging'), N'Has_Virtual_Accounts', 'SystemTypeId')) <> N'bit'
    ALTER TABLE [stg].[Party_Staging] ALTER COLUMN [Has_Virtual_Accounts] BIT NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Business_Scope') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Business_Scope] NVARCHAR(MAX) NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Ownership_Form') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Ownership_Form] NVARCHAR(150) NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Municipality') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Municipality] NVARCHAR(100) NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Phone_Number') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Phone_Number] NVARCHAR(50) NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Email_Address') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Email_Address] NVARCHAR(255) NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Website') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Website] NVARCHAR(255) NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Agent_Type') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Agent_Type] NVARCHAR(100) NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Insurance_Company') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Insurance_Company] NVARCHAR(255) NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Related_Persons_JSON') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Related_Persons_JSON] NVARCHAR(MAX) NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Related_Parties_JSON') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Related_Parties_JSON] NVARCHAR(MAX) NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Last_Update_Date') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Last_Update_Date] DATE NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Next_Renewal_Date') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Next_Renewal_Date] DATE NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Managing_LOU') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Managing_LOU] NVARCHAR(50) NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Validation_Sources') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Validation_Sources] NVARCHAR(100) NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Validation_Authority_ID') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Validation_Authority_ID] NVARCHAR(500) NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Validation_Authority_ID') IS NOT NULL
AND COL_LENGTH(N'stg.Party_Staging', N'Validation_Authority_ID') < 1000
    ALTER TABLE [stg].[Party_Staging] ALTER COLUMN [Validation_Authority_ID] NVARCHAR(500) NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Validation_Authority_Entity_ID') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Validation_Authority_Entity_ID] NVARCHAR(100) NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Direct_Parent_LEI') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Direct_Parent_LEI] NVARCHAR(20) NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Direct_Parent_Name') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Direct_Parent_Name] NVARCHAR(255) NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Direct_Parent_Relationship_Type') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Direct_Parent_Relationship_Type] NVARCHAR(100) NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Direct_Parent_Relationship_Status') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Direct_Parent_Relationship_Status] NVARCHAR(50) NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Direct_Parent_Relationship_Start_Date') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Direct_Parent_Relationship_Start_Date] DATE NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Direct_Parent_Relationship_End_Date') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Direct_Parent_Relationship_End_Date] DATE NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Ultimate_Parent_LEI') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Ultimate_Parent_LEI] NVARCHAR(20) NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Ultimate_Parent_Name') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Ultimate_Parent_Name] NVARCHAR(255) NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Ultimate_Parent_Relationship_Type') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Ultimate_Parent_Relationship_Type] NVARCHAR(100) NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Ultimate_Parent_Relationship_Status') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Ultimate_Parent_Relationship_Status] NVARCHAR(50) NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Ultimate_Parent_Relationship_Start_Date') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Ultimate_Parent_Relationship_Start_Date] DATE NULL;
IF COL_LENGTH(N'stg.Party_Staging', N'Ultimate_Parent_Relationship_End_Date') IS NULL
    ALTER TABLE [stg].[Party_Staging] ADD [Ultimate_Parent_Relationship_End_Date] DATE NULL;
GO

IF OBJECT_ID(N'[stg].[Person_Preprocessed]', N'U') IS NULL
BEGIN
    CREATE TABLE [stg].[Person_Preprocessed] (
        [Preprocessed_ID] BIGINT IDENTITY(1,1) NOT NULL,
        [Staging_ID] BIGINT NOT NULL,
        [ImportBatch_ID] BIGINT NOT NULL,
        [RawFile_ID] BIGINT NOT NULL,
        [Source_Record_ID] NVARCHAR(100) NULL,
        [PESEL_Normalized] NVARCHAR(20) NULL,
        [First_Name_Normalized] NVARCHAR(100) NULL,
        [Second_Name_Normalized] NVARCHAR(100) NULL,
        [Last_Name_Normalized] NVARCHAR(100) NULL,
        [Family_Name_Normalized] NVARCHAR(100) NULL,
        [Full_Name_Normalized] NVARCHAR(255) NULL,
        [Phone_Normalized] NVARCHAR(50) NULL,
        [Email_Normalized] NVARCHAR(255) NULL,
        [Street_Normalized] NVARCHAR(150) NULL,
        [Building_Number_Normalized] NVARCHAR(30) NULL,
        [Apartment_Number_Normalized] NVARCHAR(30) NULL,
        [City_Normalized] NVARCHAR(100) NULL,
        [Postal_Code_Normalized] NVARCHAR(20) NULL,
        [Country_Normalized] NVARCHAR(100) NULL,
        [Full_Address_Normalized] NVARCHAR(500) NULL,
        [Preprocessing_Rules_JSON] NVARCHAR(MAX) NULL,
        [Created_At] DATETIME2(0) NOT NULL CONSTRAINT [DF_Person_Preprocessed_Created_At] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [PK_Person_Preprocessed] PRIMARY KEY CLUSTERED ([Preprocessed_ID]),
        CONSTRAINT [FK_Person_Preprocessed_Staging] FOREIGN KEY ([Staging_ID])
            REFERENCES [stg].[Person_Staging] ([Staging_ID]),
        CONSTRAINT [FK_Person_Preprocessed_ImportBatch] FOREIGN KEY ([ImportBatch_ID])
            REFERENCES [meta].[ImportBatch] ([ImportBatch_ID]),
        CONSTRAINT [FK_Person_Preprocessed_RawFile] FOREIGN KEY ([RawFile_ID])
            REFERENCES [raw].[RawFile] ([RawFile_ID]),
        CONSTRAINT [UQ_Person_Preprocessed_Staging] UNIQUE ([Staging_ID]),
        CONSTRAINT [CK_Person_Preprocessed_Rules_JSON] CHECK ([Preprocessing_Rules_JSON] IS NULL OR ISJSON([Preprocessing_Rules_JSON]) = 1)
    );
END;
GO

IF OBJECT_ID(N'[stg].[Party_Preprocessed]', N'U') IS NULL
BEGIN
    CREATE TABLE [stg].[Party_Preprocessed] (
        [Preprocessed_ID] BIGINT IDENTITY(1,1) NOT NULL,
        [Staging_ID] BIGINT NOT NULL,
        [ImportBatch_ID] BIGINT NOT NULL,
        [RawFile_ID] BIGINT NOT NULL,
        [Source_Record_ID] NVARCHAR(100) NULL,
        [Name_Normalized] NVARCHAR(255) NULL,
        [Short_Name_Normalized] NVARCHAR(255) NULL,
        [Legal_Entity_Type_Normalized] NVARCHAR(100) NULL,
        [NIP_Normalized] NVARCHAR(20) NULL,
        [REGON_Normalized] NVARCHAR(20) NULL,
        [KRS_Normalized] NVARCHAR(20) NULL,
        [LEI_Normalized] NVARCHAR(30) NULL,
        [Phone_Normalized] NVARCHAR(50) NULL,
        [Email_Normalized] NVARCHAR(255) NULL,
        [Website_Normalized] NVARCHAR(255) NULL,
        [Street_Normalized] NVARCHAR(150) NULL,
        [Building_Number_Normalized] NVARCHAR(30) NULL,
        [Apartment_Number_Normalized] NVARCHAR(30) NULL,
        [City_Normalized] NVARCHAR(100) NULL,
        [Postal_Code_Normalized] NVARCHAR(20) NULL,
        [Country_Normalized] NVARCHAR(100) NULL,
        [Full_Address_Normalized] NVARCHAR(500) NULL,
        [Preprocessing_Rules_JSON] NVARCHAR(MAX) NULL,
        [Created_At] DATETIME2(0) NOT NULL CONSTRAINT [DF_Party_Preprocessed_Created_At] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [PK_Party_Preprocessed] PRIMARY KEY CLUSTERED ([Preprocessed_ID]),
        CONSTRAINT [FK_Party_Preprocessed_Staging] FOREIGN KEY ([Staging_ID])
            REFERENCES [stg].[Party_Staging] ([Staging_ID]),
        CONSTRAINT [FK_Party_Preprocessed_ImportBatch] FOREIGN KEY ([ImportBatch_ID])
            REFERENCES [meta].[ImportBatch] ([ImportBatch_ID]),
        CONSTRAINT [FK_Party_Preprocessed_RawFile] FOREIGN KEY ([RawFile_ID])
            REFERENCES [raw].[RawFile] ([RawFile_ID]),
        CONSTRAINT [UQ_Party_Preprocessed_Staging] UNIQUE ([Staging_ID]),
        CONSTRAINT [CK_Party_Preprocessed_Rules_JSON] CHECK ([Preprocessing_Rules_JSON] IS NULL OR ISJSON([Preprocessing_Rules_JSON]) = 1)
    );
END;
GO

IF OBJECT_ID(N'[stg].[Validation_Result]', N'U') IS NULL
BEGIN
    CREATE TABLE [stg].[Validation_Result] (
        [Validation_ID] BIGINT IDENTITY(1,1) NOT NULL,
        [ImportBatch_ID] BIGINT NOT NULL,
        [RawFile_ID] BIGINT NOT NULL,
        [Entity_Type] NVARCHAR(20) NOT NULL,
        [Staging_ID] BIGINT NOT NULL,
        [Preprocessed_ID] BIGINT NULL,
        [Validation_Level] NVARCHAR(30) NOT NULL,
        [Rule_Code] NVARCHAR(100) NOT NULL,
        [Field_Name] NVARCHAR(100) NOT NULL,
        [Severity] NVARCHAR(20) NOT NULL,
        [Status] NVARCHAR(20) NOT NULL,
        [Message] NVARCHAR(MAX) NOT NULL,
        [Checked_Value] NVARCHAR(MAX) NULL,
        [Created_At] DATETIME2(0) NOT NULL CONSTRAINT [DF_Validation_Result_Created_At] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [PK_Validation_Result] PRIMARY KEY CLUSTERED ([Validation_ID]),
        CONSTRAINT [FK_Validation_Result_ImportBatch] FOREIGN KEY ([ImportBatch_ID])
            REFERENCES [meta].[ImportBatch] ([ImportBatch_ID]),
        CONSTRAINT [FK_Validation_Result_RawFile] FOREIGN KEY ([RawFile_ID])
            REFERENCES [raw].[RawFile] ([RawFile_ID]),
        CONSTRAINT [CK_Validation_Result_Entity_Type] CHECK ([Entity_Type] IN (N'PERSON', N'PARTY')),
        CONSTRAINT [CK_Validation_Result_Level] CHECK ([Validation_Level] IN (N'STAGING', N'PREPROCESSING')),
        CONSTRAINT [CK_Validation_Result_Severity] CHECK ([Severity] IN (N'INFO', N'WARNING', N'ERROR')),
        CONSTRAINT [CK_Validation_Result_Status] CHECK ([Status] IN (N'PASS', N'WARNING', N'ERROR'))
    );
END;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_ImportBatch_SourceSystem_ID' AND object_id = OBJECT_ID(N'[meta].[ImportBatch]'))
    CREATE INDEX [IX_ImportBatch_SourceSystem_ID] ON [meta].[ImportBatch] ([SourceSystem_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_ColumnMapping_SourceSystem_Entity' AND object_id = OBJECT_ID(N'[meta].[ColumnMapping]'))
    CREATE INDEX [IX_ColumnMapping_SourceSystem_Entity] ON [meta].[ColumnMapping] ([SourceSystem_ID], [Entity_Type]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_RawFile_ImportBatch_ID' AND object_id = OBJECT_ID(N'[raw].[RawFile]'))
    CREATE INDEX [IX_RawFile_ImportBatch_ID] ON [raw].[RawFile] ([ImportBatch_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_ProcessLog_ImportBatch_ID' AND object_id = OBJECT_ID(N'[meta].[ProcessLog]'))
    CREATE INDEX [IX_ProcessLog_ImportBatch_ID] ON [meta].[ProcessLog] ([ImportBatch_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_ProcessLog_RawFile_ID' AND object_id = OBJECT_ID(N'[meta].[ProcessLog]'))
    CREATE INDEX [IX_ProcessLog_RawFile_ID] ON [meta].[ProcessLog] ([RawFile_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_ProcessLog_Step_Name_Status' AND object_id = OBJECT_ID(N'[meta].[ProcessLog]'))
    CREATE INDEX [IX_ProcessLog_Step_Name_Status] ON [meta].[ProcessLog] ([Step_Name], [Step_Status]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Person_Staging_ImportBatch_ID' AND object_id = OBJECT_ID(N'[stg].[Person_Staging]'))
    CREATE INDEX [IX_Person_Staging_ImportBatch_ID] ON [stg].[Person_Staging] ([ImportBatch_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Person_Staging_RawFile_ID' AND object_id = OBJECT_ID(N'[stg].[Person_Staging]'))
    CREATE INDEX [IX_Person_Staging_RawFile_ID] ON [stg].[Person_Staging] ([RawFile_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Party_Staging_ImportBatch_ID' AND object_id = OBJECT_ID(N'[stg].[Party_Staging]'))
    CREATE INDEX [IX_Party_Staging_ImportBatch_ID] ON [stg].[Party_Staging] ([ImportBatch_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Party_Staging_RawFile_ID' AND object_id = OBJECT_ID(N'[stg].[Party_Staging]'))
    CREATE INDEX [IX_Party_Staging_RawFile_ID] ON [stg].[Party_Staging] ([RawFile_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Person_Preprocessed_RawFile_ID' AND object_id = OBJECT_ID(N'[stg].[Person_Preprocessed]'))
    CREATE INDEX [IX_Person_Preprocessed_RawFile_ID] ON [stg].[Person_Preprocessed] ([RawFile_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Person_Preprocessed_Match' AND object_id = OBJECT_ID(N'[stg].[Person_Preprocessed]'))
    CREATE INDEX [IX_Person_Preprocessed_Match] ON [stg].[Person_Preprocessed] ([PESEL_Normalized], [Full_Name_Normalized]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Party_Preprocessed_RawFile_ID' AND object_id = OBJECT_ID(N'[stg].[Party_Preprocessed]'))
    CREATE INDEX [IX_Party_Preprocessed_RawFile_ID] ON [stg].[Party_Preprocessed] ([RawFile_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Party_Preprocessed_Match' AND object_id = OBJECT_ID(N'[stg].[Party_Preprocessed]'))
    CREATE INDEX [IX_Party_Preprocessed_Match] ON [stg].[Party_Preprocessed] ([NIP_Normalized], [REGON_Normalized], [KRS_Normalized]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Validation_Result_RawFile_Entity' AND object_id = OBJECT_ID(N'[stg].[Validation_Result]'))
    CREATE INDEX [IX_Validation_Result_RawFile_Entity] ON [stg].[Validation_Result] ([RawFile_ID], [Entity_Type]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Validation_Result_Status' AND object_id = OBJECT_ID(N'[stg].[Validation_Result]'))
    CREATE INDEX [IX_Validation_Result_Status] ON [stg].[Validation_Result] ([Status], [Rule_Code]);
GO

MERGE [meta].[SourceSystem] AS target
USING (VALUES
    (N'CEIDG', N'Centralna Ewidencja i Informacja o Dzialalnosci Gospodarczej', 80),
    (N'KRS', N'Krajowy Rejestr Sadowy', 90),
    (N'REGON', N'Rejestr REGON', 85),
    (N'VAT', N'Wykaz podatnikow VAT', 85),
    (N'PESEL', N'Rejestr PESEL', 90),
    (N'KNF_AGENT', N'KNF Rejestr posrednikow ubezpieczeniowych - agent', 80),
    (N'KNF_PRACOWNIK_AGENTA', N'KNF Rejestr posrednikow ubezpieczeniowych - pracownik agenta', 80),
    (N'KNF_FIRMY_INWESTYCYJNE', N'KNF Rejestr firm inwestycyjnych', 80),
    (N'KNF_PIENIADZ_ELEKTRONICZNY', N'KNF Rejestr dostawcow i wydawcow pieniadza elektronicznego', 80),
    (N'GLEIF', N'GLEIF', 75),
    (N'INSURANCE_CORE', N'Oracle Insurance Core - relacyjne zrodlo przez ODBC', 70)
) AS source ([SourceSystem_Code], [SourceSystem_Name], [Trust_Level])
ON target.[SourceSystem_Code] = source.[SourceSystem_Code]
WHEN NOT MATCHED THEN
    INSERT ([SourceSystem_Code], [SourceSystem_Name], [Trust_Level])
    VALUES (source.[SourceSystem_Code], source.[SourceSystem_Name], source.[Trust_Level]);
GO

DECLARE @INSURANCE_CORE_SourceSystem_ID INT = (
    SELECT [SourceSystem_ID]
    FROM [meta].[SourceSystem]
    WHERE [SourceSystem_Code] = N'INSURANCE_CORE'
);

DELETE FROM [meta].[ColumnMapping]
WHERE [SourceSystem_ID] = @INSURANCE_CORE_SourceSystem_ID;

MERGE [meta].[ColumnMapping] AS target
USING (VALUES
    (@INSURANCE_CORE_SourceSystem_ID, N'PARTY', N'EXT_REF_NO', N'Source_Record_ID'),
    (@INSURANCE_CORE_SourceSystem_ID, N'PARTY', N'PARTY_LABEL', N'Name'),
    (@INSURANCE_CORE_SourceSystem_ID, N'PARTY', N'BRAND_LABEL', N'Short_Name'),
    (@INSURANCE_CORE_SourceSystem_ID, N'PARTY', N'FORM_CD', N'Legal_Entity_Type'),
    (@INSURANCE_CORE_SourceSystem_ID, N'PARTY', N'ACTIVATION_DT', N'Establishment_Date'),
    (@INSURANCE_CORE_SourceSystem_ID, N'PARTY', N'TERMINATION_DT', N'Deregistration_Date'),
    (@INSURANCE_CORE_SourceSystem_ID, N'PARTY', N'LIFE_CYCLE_CD', N'Register_Status'),
    (@INSURANCE_CORE_SourceSystem_ID, N'PARTY', N'TAX_REF', N'Identifiers_JSON'),
    (@INSURANCE_CORE_SourceSystem_ID, N'PARTY', N'STAT_REG_REF', N'Identifiers_JSON'),
    (@INSURANCE_CORE_SourceSystem_ID, N'PARTY', N'COURT_REF', N'Identifiers_JSON'),
    (@INSURANCE_CORE_SourceSystem_ID, N'PARTY', N'ADDR_TXT', N'Street'),
    (@INSURANCE_CORE_SourceSystem_ID, N'PARTY', N'MUNICIPAL_UNIT', N'City'),
    (@INSURANCE_CORE_SourceSystem_ID, N'PARTY', N'POST_AREA', N'Postal_Code'),
    (@INSURANCE_CORE_SourceSystem_ID, N'PARTY', N'ISO_MARKET', N'Country'),
    (@INSURANCE_CORE_SourceSystem_ID, N'PARTY', N'TEL_NOTE', N'Phone_Number'),
    (@INSURANCE_CORE_SourceSystem_ID, N'PARTY', N'MAILBOX', N'Email_Address'),
    (@INSURANCE_CORE_SourceSystem_ID, N'PARTY', N'SETTLEMENT_ACC', N'Bank_Accounts_JSON'),
    (@INSURANCE_CORE_SourceSystem_ID, N'PARTY', N'AREA_BUCKET', N'Province'),
    (@INSURANCE_CORE_SourceSystem_ID, N'PARTY', N'RELATED_PERSONS_JSON', N'Related_Persons_JSON'),
    (@INSURANCE_CORE_SourceSystem_ID, N'PARTY', N'RELATED_PARTIES_JSON', N'Related_Parties_JSON'),
    (@INSURANCE_CORE_SourceSystem_ID, N'PERSON', N'PERSON_REF', N'Source_Record_ID'),
    (@INSURANCE_CORE_SourceSystem_ID, N'PERSON', N'NATIONAL_REF', N'PESEL'),
    (@INSURANCE_CORE_SourceSystem_ID, N'PERSON', N'GIVEN_TXT', N'First_Name'),
    (@INSURANCE_CORE_SourceSystem_ID, N'PERSON', N'SECOND_GIVEN_TXT', N'Second_Name'),
    (@INSURANCE_CORE_SourceSystem_ID, N'PERSON', N'FAMILY_TXT', N'Last_Name'),
    (@INSURANCE_CORE_SourceSystem_ID, N'PERSON', N'BIRTH_DT_HINT', N'Birth_Date'),
    (@INSURANCE_CORE_SourceSystem_ID, N'PERSON', N'BIRTH_PLACE_HINT', N'Place_Of_Birth'),
    (@INSURANCE_CORE_SourceSystem_ID, N'PERSON', N'GENDER_HINT', N'Sex'),
    (@INSURANCE_CORE_SourceSystem_ID, N'PERSON', N'CITIZENSHIP_HINT', N'Citizenship'),
    (@INSURANCE_CORE_SourceSystem_ID, N'PERSON', N'MAILBOX', N'Email_Address'),
    (@INSURANCE_CORE_SourceSystem_ID, N'PERSON', N'TEL_NOTE', N'Phone_Number'),
    (@INSURANCE_CORE_SourceSystem_ID, N'PERSON', N'ADDR_TXT', N'Street'),
    (@INSURANCE_CORE_SourceSystem_ID, N'PERSON', N'MUNICIPAL_UNIT', N'City'),
    (@INSURANCE_CORE_SourceSystem_ID, N'PERSON', N'POST_AREA', N'Postal_Code'),
    (@INSURANCE_CORE_SourceSystem_ID, N'PERSON', N'ISO_MARKET', N'Country')
) AS source ([SourceSystem_ID], [Entity_Type], [Source_Column_Name], [Canonical_Column_Name])
ON target.[SourceSystem_ID] = source.[SourceSystem_ID]
AND target.[Entity_Type] = source.[Entity_Type]
AND target.[Source_Column_Name] = source.[Source_Column_Name]
WHEN NOT MATCHED THEN
    INSERT ([SourceSystem_ID], [Entity_Type], [Source_Column_Name], [Canonical_Column_Name])
    VALUES (source.[SourceSystem_ID], source.[Entity_Type], source.[Source_Column_Name], source.[Canonical_Column_Name]);
GO

DECLARE @CEIDG_SourceSystem_ID INT = (
    SELECT [SourceSystem_ID]
    FROM [meta].[SourceSystem]
    WHERE [SourceSystem_Code] = N'CEIDG'
);

DELETE FROM [meta].[ColumnMapping]
WHERE [SourceSystem_ID] = @CEIDG_SourceSystem_ID
AND [Source_Column_Name] IN (
    N'firstName', N'imie', N'surname', N'nazwisko', N'pesel',
    N'name', N'nazwa', N'nazwa_firmy', N'nip', N'regon', N'krs'
);

MERGE [meta].[ColumnMapping] AS target
USING (VALUES
    -- PERSON (CEIDG)
    (@CEIDG_SourceSystem_ID, N'PERSON', N'firma.wlasciciel.pesel', N'PESEL'),
    (@CEIDG_SourceSystem_ID, N'PERSON', N'firma.wlasciciel.imie', N'First_Name'),
    (@CEIDG_SourceSystem_ID, N'PERSON', N'firma.wlasciciel.drugieImie', N'Second_Name'),
    (@CEIDG_SourceSystem_ID, N'PERSON', N'firma.wlasciciel.nazwisko', N'Last_Name'),
    (@CEIDG_SourceSystem_ID, N'PERSON', N'firma.telefon', N'Phone_Number'),
    (@CEIDG_SourceSystem_ID, N'PERSON', N'firma.email', N'Email_Address'),
    -- CEIDG adresy są w 1 polu tekstowym; wrzucamy oba do Street (później można je sparsować)
    (@CEIDG_SourceSystem_ID, N'PERSON', N'firma.adresDzialalnosci', N'Street'),
    (@CEIDG_SourceSystem_ID, N'PERSON', N'firma.adresKorespondencyjny', N'Street'),

    -- PARTY (CEIDG)
    (@CEIDG_SourceSystem_ID, N'PARTY', N'firma.nazwa', N'Name'),
    (@CEIDG_SourceSystem_ID, N'PARTY', N'firma.skroconaNazwa', N'Short_Name'),
    (@CEIDG_SourceSystem_ID, N'PARTY', N'firma.dataRozpoczeciaDzialalnosci', N'Establishment_Date'),
    (@CEIDG_SourceSystem_ID, N'PARTY', N'firma.przewazajacePKD', N'Business_Scope'),
    -- CEIDG adresy są w 1 polu tekstowym; wrzucamy oba do Street (później można je sparsować)
    (@CEIDG_SourceSystem_ID, N'PARTY', N'firma.adresDzialalnosci', N'Street'),
    (@CEIDG_SourceSystem_ID, N'PARTY', N'firma.adresKorespondencyjny', N'Street'),
    (@CEIDG_SourceSystem_ID, N'PARTY', N'firma.nip', N'Identifiers_JSON'),
    (@CEIDG_SourceSystem_ID, N'PARTY', N'firma.regon', N'Identifiers_JSON')
) AS source ([SourceSystem_ID], [Entity_Type], [Source_Column_Name], [Canonical_Column_Name])
ON target.[SourceSystem_ID] = source.[SourceSystem_ID]
AND target.[Entity_Type] = source.[Entity_Type]
AND target.[Source_Column_Name] = source.[Source_Column_Name]
WHEN NOT MATCHED THEN
    INSERT ([SourceSystem_ID], [Entity_Type], [Source_Column_Name], [Canonical_Column_Name])
    VALUES (source.[SourceSystem_ID], source.[Entity_Type], source.[Source_Column_Name], source.[Canonical_Column_Name]);
GO

DECLARE @GLEIF_SourceSystem_ID INT = (
    SELECT [SourceSystem_ID]
    FROM [meta].[SourceSystem]
    WHERE [SourceSystem_Code] = N'GLEIF'
);

DELETE FROM [meta].[ColumnMapping]
WHERE [SourceSystem_ID] = @GLEIF_SourceSystem_ID
AND [Entity_Type] = N'PARTY'
AND [Source_Column_Name] IN (
    N'DirectParentLEI',
    N'UltimateParentLEI',
    N'ValidationAuthorityID',
    N'ValidationAuthorityEntityID'
);

MERGE [meta].[ColumnMapping] AS target
USING (VALUES
    -- PARTY (scalony GLEIF) - data/*/gleif.*
    (@GLEIF_SourceSystem_ID, N'PARTY', N'LegalName', N'Name'),
    (@GLEIF_SourceSystem_ID, N'PARTY', N'LegalJurisdiction', N'Registration_Country'),
    (@GLEIF_SourceSystem_ID, N'PARTY', N'EntityLegalFormCode', N'Legal_Entity_Type'),
    (@GLEIF_SourceSystem_ID, N'PARTY', N'InitialRegistrationDate', N'Establishment_Date'),
    (@GLEIF_SourceSystem_ID, N'PARTY', N'FirstAddressLine', N'Street'),
    (@GLEIF_SourceSystem_ID, N'PARTY', N'City', N'City'),
    (@GLEIF_SourceSystem_ID, N'PARTY', N'PostalCode', N'Postal_Code'),
    (@GLEIF_SourceSystem_ID, N'PARTY', N'Country', N'Country'),
    (@GLEIF_SourceSystem_ID, N'PARTY', N'RegistrationStatus', N'Registration_Status'),
    (@GLEIF_SourceSystem_ID, N'PARTY', N'LastUpdateDate', N'Last_Update_Date'),
    (@GLEIF_SourceSystem_ID, N'PARTY', N'NextRenewalDate', N'Next_Renewal_Date'),
    (@GLEIF_SourceSystem_ID, N'PARTY', N'ManagingLOU', N'Managing_LOU'),
    (@GLEIF_SourceSystem_ID, N'PARTY', N'ValidationSources', N'Validation_Sources'),
    (@GLEIF_SourceSystem_ID, N'PARTY', N'RegisteredAt', N'Validation_Authority_ID'),
    (@GLEIF_SourceSystem_ID, N'PARTY', N'Registered At', N'Validation_Authority_ID'),
    (@GLEIF_SourceSystem_ID, N'PARTY', N'RegisteredAs', N'Validation_Authority_Entity_ID'),
    (@GLEIF_SourceSystem_ID, N'PARTY', N'Registered As', N'Validation_Authority_Entity_ID'),
    (@GLEIF_SourceSystem_ID, N'PARTY', N'LEI', N'Identifiers_JSON'),
    (@GLEIF_SourceSystem_ID, N'PARTY', N'DirectParentLEI', N'Direct_Parent_LEI'),
    (@GLEIF_SourceSystem_ID, N'PARTY', N'DirectParentName', N'Direct_Parent_Name'),
    (@GLEIF_SourceSystem_ID, N'PARTY', N'DirectParentRelationshipType', N'Direct_Parent_Relationship_Type'),
    (@GLEIF_SourceSystem_ID, N'PARTY', N'DirectParentRelationshipStatus', N'Direct_Parent_Relationship_Status'),
    (@GLEIF_SourceSystem_ID, N'PARTY', N'DirectParentRelationshipStartDate', N'Direct_Parent_Relationship_Start_Date'),
    (@GLEIF_SourceSystem_ID, N'PARTY', N'DirectParentRelationshipEndDate', N'Direct_Parent_Relationship_End_Date'),
    (@GLEIF_SourceSystem_ID, N'PARTY', N'UltimateParentLEI', N'Ultimate_Parent_LEI'),
    (@GLEIF_SourceSystem_ID, N'PARTY', N'UltimateParentName', N'Ultimate_Parent_Name'),
    (@GLEIF_SourceSystem_ID, N'PARTY', N'UltimateParentRelationshipType', N'Ultimate_Parent_Relationship_Type'),
    (@GLEIF_SourceSystem_ID, N'PARTY', N'UltimateParentRelationshipStatus', N'Ultimate_Parent_Relationship_Status'),
    (@GLEIF_SourceSystem_ID, N'PARTY', N'UltimateParentRelationshipStartDate', N'Ultimate_Parent_Relationship_Start_Date'),
    (@GLEIF_SourceSystem_ID, N'PARTY', N'UltimateParentRelationshipEndDate', N'Ultimate_Parent_Relationship_End_Date')
) AS source ([SourceSystem_ID], [Entity_Type], [Source_Column_Name], [Canonical_Column_Name])
ON target.[SourceSystem_ID] = source.[SourceSystem_ID]
AND target.[Entity_Type] = source.[Entity_Type]
AND target.[Source_Column_Name] = source.[Source_Column_Name]
WHEN NOT MATCHED THEN
    INSERT ([SourceSystem_ID], [Entity_Type], [Source_Column_Name], [Canonical_Column_Name])
    VALUES (source.[SourceSystem_ID], source.[Entity_Type], source.[Source_Column_Name], source.[Canonical_Column_Name]);
GO

DECLARE @KRS_SourceSystem_ID INT = (
    SELECT [SourceSystem_ID]
    FROM [meta].[SourceSystem]
    WHERE [SourceSystem_Code] = N'KRS'
);

DELETE FROM [meta].[ColumnMapping]
WHERE [SourceSystem_ID] = @KRS_SourceSystem_ID
AND [Entity_Type] = N'PARTY'
AND [Source_Column_Name] IN (
    N'WspolnikPodmiot1_Nazwa',
    N'WspolnikPodmiot1_KRS',
    N'WspolnikPodmiot1_NIP'
);

MERGE [meta].[ColumnMapping] AS target
USING (VALUES
    -- PERSON (KRS) - pierwszy znaleziony slot osoby powiązanej w rekordzie
    (@KRS_SourceSystem_ID, N'PERSON', N'CzlonekZarzadu1_Imie', N'First_Name'),
    (@KRS_SourceSystem_ID, N'PERSON', N'CzlonekZarzadu1_Nazwisko', N'Last_Name'),
    (@KRS_SourceSystem_ID, N'PERSON', N'CzlonekZarzadu1_PESEL', N'PESEL'),
    (@KRS_SourceSystem_ID, N'PERSON', N'Prokurent1_Imie', N'First_Name'),
    (@KRS_SourceSystem_ID, N'PERSON', N'Prokurent1_Nazwisko', N'Last_Name'),
    (@KRS_SourceSystem_ID, N'PERSON', N'Prokurent1_PESEL', N'PESEL'),
    (@KRS_SourceSystem_ID, N'PERSON', N'WspolnikOsoba1_Imie', N'First_Name'),
    (@KRS_SourceSystem_ID, N'PERSON', N'WspolnikOsoba1_Nazwisko', N'Last_Name'),
    (@KRS_SourceSystem_ID, N'PERSON', N'WspolnikOsoba1_PESEL', N'PESEL'),
    (@KRS_SourceSystem_ID, N'PERSON', N'Likwidator1_Imie', N'First_Name'),
    (@KRS_SourceSystem_ID, N'PERSON', N'Likwidator1_Nazwisko', N'Last_Name'),
    (@KRS_SourceSystem_ID, N'PERSON', N'Likwidator1_PESEL', N'PESEL'),
    (@KRS_SourceSystem_ID, N'PERSON', N'CzlonekRadyNadzorczej1_Imie', N'First_Name'),
    (@KRS_SourceSystem_ID, N'PERSON', N'CzlonekRadyNadzorczej1_Nazwisko', N'Last_Name'),
    (@KRS_SourceSystem_ID, N'PERSON', N'CzlonekRadyNadzorczej1_PESEL', N'PESEL'),

    -- PARTY (KRS) - data/csv/krs.csv
    (@KRS_SourceSystem_ID, N'PARTY', N'nazwa', N'Name'),
    (@KRS_SourceSystem_ID, N'PARTY', N'nazwaSkrocona', N'Short_Name'),
    (@KRS_SourceSystem_ID, N'PARTY', N'formaPrawna', N'Legal_Entity_Type'),
    (@KRS_SourceSystem_ID, N'PARTY', N'dataRejestracji', N'Establishment_Date'),
    (@KRS_SourceSystem_ID, N'PARTY', N'status', N'Register_Status'),
    (@KRS_SourceSystem_ID, N'PARTY', N'pkd', N'Business_Scope'),
    (@KRS_SourceSystem_ID, N'PARTY', N'siedziba', N'City'),
    (@KRS_SourceSystem_ID, N'PARTY', N'adres', N'Street'),
    (@KRS_SourceSystem_ID, N'PARTY', N'nip', N'Identifiers_JSON'),
    (@KRS_SourceSystem_ID, N'PARTY', N'regon', N'Identifiers_JSON'),
    (@KRS_SourceSystem_ID, N'PARTY', N'numerKRS', N'Identifiers_JSON')
) AS source ([SourceSystem_ID], [Entity_Type], [Source_Column_Name], [Canonical_Column_Name])
ON target.[SourceSystem_ID] = source.[SourceSystem_ID]
AND target.[Entity_Type] = source.[Entity_Type]
AND target.[Source_Column_Name] = source.[Source_Column_Name]
WHEN NOT MATCHED THEN
    INSERT ([SourceSystem_ID], [Entity_Type], [Source_Column_Name], [Canonical_Column_Name])
    VALUES (source.[SourceSystem_ID], source.[Entity_Type], source.[Source_Column_Name], source.[Canonical_Column_Name]);
GO

DECLARE @REGON_SourceSystem_ID INT = (
    SELECT [SourceSystem_ID]
    FROM [meta].[SourceSystem]
    WHERE [SourceSystem_Code] = N'REGON'
);

MERGE [meta].[ColumnMapping] AS target
USING (VALUES
    -- PARTY (REGON) - data/csv/regon.csv
    (@REGON_SourceSystem_ID, N'PARTY', N'nazwa', N'Name'),
    (@REGON_SourceSystem_ID, N'PARTY', N'formaPrawna', N'Legal_Entity_Type'),
    (@REGON_SourceSystem_ID, N'PARTY', N'dataPowstania', N'Establishment_Date'),
    (@REGON_SourceSystem_ID, N'PARTY', N'adresSiedziby', N'Street'),
    (@REGON_SourceSystem_ID, N'PARTY', N'miejscowosc', N'City'),
    (@REGON_SourceSystem_ID, N'PARTY', N'kodPocztowy', N'Postal_Code'),
    (@REGON_SourceSystem_ID, N'PARTY', N'powiat', N'District'),
    (@REGON_SourceSystem_ID, N'PARTY', N'wojewodztwo', N'Province'),
    (@REGON_SourceSystem_ID, N'PARTY', N'pkd', N'Business_Scope'),
    (@REGON_SourceSystem_ID, N'PARTY', N'formaWlasnosci', N'Ownership_Form'),
    (@REGON_SourceSystem_ID, N'PARTY', N'gmina', N'Municipality'),
    (@REGON_SourceSystem_ID, N'PARTY', N'telefon', N'Phone_Number'),
    (@REGON_SourceSystem_ID, N'PARTY', N'email', N'Email_Address'),
    (@REGON_SourceSystem_ID, N'PARTY', N'stronaWWW', N'Website'),
    (@REGON_SourceSystem_ID, N'PARTY', N'nip', N'Identifiers_JSON'),
    (@REGON_SourceSystem_ID, N'PARTY', N'krs', N'Identifiers_JSON'),
    (@REGON_SourceSystem_ID, N'PARTY', N'regon', N'Identifiers_JSON')
) AS source ([SourceSystem_ID], [Entity_Type], [Source_Column_Name], [Canonical_Column_Name])
ON target.[SourceSystem_ID] = source.[SourceSystem_ID]
AND target.[Entity_Type] = source.[Entity_Type]
AND target.[Source_Column_Name] = source.[Source_Column_Name]
WHEN NOT MATCHED THEN
    INSERT ([SourceSystem_ID], [Entity_Type], [Source_Column_Name], [Canonical_Column_Name])
    VALUES (source.[SourceSystem_ID], source.[Entity_Type], source.[Source_Column_Name], source.[Canonical_Column_Name]);
GO

DECLARE @VAT_SourceSystem_ID INT = (
    SELECT [SourceSystem_ID]
    FROM [meta].[SourceSystem]
    WHERE [SourceSystem_Code] = N'VAT'
);

MERGE [meta].[ColumnMapping] AS target
USING (VALUES
    -- PARTY (VAT) - data/csv/vat.csv
    (@VAT_SourceSystem_ID, N'PARTY', N'name', N'Name'),
    (@VAT_SourceSystem_ID, N'PARTY', N'registrationLegalDate', N'Establishment_Date'),
    (@VAT_SourceSystem_ID, N'PARTY', N'statusVat', N'Register_Status'),
    (@VAT_SourceSystem_ID, N'PARTY', N'removalDate', N'Deregistration_Date'),
    (@VAT_SourceSystem_ID, N'PARTY', N'accountNumbers', N'Bank_Accounts_JSON'),
    (@VAT_SourceSystem_ID, N'PARTY', N'hasVirtualAccounts', N'Has_Virtual_Accounts'),
    (@VAT_SourceSystem_ID, N'PARTY', N'workingAddress', N'Street'),
    (@VAT_SourceSystem_ID, N'PARTY', N'residenceAddress', N'Postal_City'),
    (@VAT_SourceSystem_ID, N'PARTY', N'nip', N'Identifiers_JSON'),
    (@VAT_SourceSystem_ID, N'PARTY', N'regon', N'Identifiers_JSON'),
    (@VAT_SourceSystem_ID, N'PARTY', N'krs', N'Identifiers_JSON')
) AS source ([SourceSystem_ID], [Entity_Type], [Source_Column_Name], [Canonical_Column_Name])
ON target.[SourceSystem_ID] = source.[SourceSystem_ID]
AND target.[Entity_Type] = source.[Entity_Type]
AND target.[Source_Column_Name] = source.[Source_Column_Name]
WHEN NOT MATCHED THEN
    INSERT ([SourceSystem_ID], [Entity_Type], [Source_Column_Name], [Canonical_Column_Name])
    VALUES (source.[SourceSystem_ID], source.[Entity_Type], source.[Source_Column_Name], source.[Canonical_Column_Name]);
GO

DECLARE @PESEL_SourceSystem_ID INT = (
    SELECT [SourceSystem_ID]
    FROM [meta].[SourceSystem]
    WHERE [SourceSystem_Code] = N'PESEL'
);

MERGE [meta].[ColumnMapping] AS target
USING (VALUES
    -- PERSON (PESEL) - data/csv/pesel.csv
    (@PESEL_SourceSystem_ID, N'PERSON', N'PESEL', N'PESEL'),
    (@PESEL_SourceSystem_ID, N'PERSON', N'NumerDowoduOsobistego', N'Serial_Number_ID_Card'),
    (@PESEL_SourceSystem_ID, N'PERSON', N'NumerPaszportu', N'Serial_Number_Passport'),
    (@PESEL_SourceSystem_ID, N'PERSON', N'Imie', N'First_Name'),
    (@PESEL_SourceSystem_ID, N'PERSON', N'DrugieImie', N'Second_Name'),
    (@PESEL_SourceSystem_ID, N'PERSON', N'Nazwisko', N'Last_Name'),
    (@PESEL_SourceSystem_ID, N'PERSON', N'NazwiskoRodowe', N'Family_Name'),
    (@PESEL_SourceSystem_ID, N'PERSON', N'DataUrodzenia', N'Birth_Date'),
    (@PESEL_SourceSystem_ID, N'PERSON', N'MiejsceUrodzenia', N'Place_Of_Birth'),
    (@PESEL_SourceSystem_ID, N'PERSON', N'Plec', N'Sex'),
    (@PESEL_SourceSystem_ID, N'PERSON', N'Obywatelstwo', N'Citizenship'),
    (@PESEL_SourceSystem_ID, N'PERSON', N'Telefon', N'Phone_Number'),
    (@PESEL_SourceSystem_ID, N'PERSON', N'Email', N'Email_Address'),
    (@PESEL_SourceSystem_ID, N'PERSON', N'AdresZameldowania', N'Street'),
    (@PESEL_SourceSystem_ID, N'PERSON', N'AdresKorespondencyjny', N'Postal_City')
) AS source ([SourceSystem_ID], [Entity_Type], [Source_Column_Name], [Canonical_Column_Name])
ON target.[SourceSystem_ID] = source.[SourceSystem_ID]
AND target.[Entity_Type] = source.[Entity_Type]
AND target.[Source_Column_Name] = source.[Source_Column_Name]
WHEN NOT MATCHED THEN
    INSERT ([SourceSystem_ID], [Entity_Type], [Source_Column_Name], [Canonical_Column_Name])
    VALUES (source.[SourceSystem_ID], source.[Entity_Type], source.[Source_Column_Name], source.[Canonical_Column_Name]);
GO

DECLARE @KNF_AGENT_SourceSystem_ID INT = (
    SELECT [SourceSystem_ID]
    FROM [meta].[SourceSystem]
    WHERE [SourceSystem_Code] = N'KNF_AGENT'
);

MERGE [meta].[ColumnMapping] AS target
USING (VALUES
    -- PERSON (KNF_AGENT) - data/csv/KNF_Rejestr_posrednikow_ubezpieczeniowych_agent.csv
    (@KNF_AGENT_SourceSystem_ID, N'PERSON', N'Imię', N'First_Name'),
    (@KNF_AGENT_SourceSystem_ID, N'PERSON', N'Nazwisko', N'Last_Name'),
    (@KNF_AGENT_SourceSystem_ID, N'PERSON', N'PESEL', N'PESEL'),

    -- PARTY (KNF_AGENT)
    (@KNF_AGENT_SourceSystem_ID, N'PARTY', N'Firma/Nazwa', N'Name'),
    (@KNF_AGENT_SourceSystem_ID, N'PARTY', N'Miejscowość', N'City'),
    (@KNF_AGENT_SourceSystem_ID, N'PARTY', N'Ulica i numer', N'Street'),
    (@KNF_AGENT_SourceSystem_ID, N'PARTY', N'Kod pocztowy', N'Postal_Code'),
    (@KNF_AGENT_SourceSystem_ID, N'PARTY', N'Numer NIP', N'Identifiers_JSON'),
    (@KNF_AGENT_SourceSystem_ID, N'PARTY', N'Numer KRS', N'Identifiers_JSON'),
    (@KNF_AGENT_SourceSystem_ID, N'PARTY', N'Numer agenta', N'Source_Record_ID'),
    (@KNF_AGENT_SourceSystem_ID, N'PARTY', N'Zakład ubezpieczeń', N'Insurance_Company'),
    (@KNF_AGENT_SourceSystem_ID, N'PARTY', N'Rodzaj agenta', N'Agent_Type'),
    (@KNF_AGENT_SourceSystem_ID, N'PARTY', N'Data wpisu', N'Registration_Date'),
    (@KNF_AGENT_SourceSystem_ID, N'PARTY', N'Data zakończenia', N'Deregistration_Date')
) AS source ([SourceSystem_ID], [Entity_Type], [Source_Column_Name], [Canonical_Column_Name])
ON target.[SourceSystem_ID] = source.[SourceSystem_ID]
AND target.[Entity_Type] = source.[Entity_Type]
AND target.[Source_Column_Name] = source.[Source_Column_Name]
WHEN NOT MATCHED THEN
    INSERT ([SourceSystem_ID], [Entity_Type], [Source_Column_Name], [Canonical_Column_Name])
    VALUES (source.[SourceSystem_ID], source.[Entity_Type], source.[Source_Column_Name], source.[Canonical_Column_Name]);
GO

DECLARE @KNF_PRACOWNIK_AGENTA_SourceSystem_ID INT = (
    SELECT [SourceSystem_ID]
    FROM [meta].[SourceSystem]
    WHERE [SourceSystem_Code] = N'KNF_PRACOWNIK_AGENTA'
);

DELETE FROM [meta].[ColumnMapping]
WHERE [SourceSystem_ID] = @KNF_PRACOWNIK_AGENTA_SourceSystem_ID
AND [Entity_Type] = N'PERSON'
AND [Source_Column_Name] IN (N'Imię agenta', N'Nazwisko agenta');

MERGE [meta].[ColumnMapping] AS target
USING (VALUES
    -- PERSON (KNF_PRACOWNIK_AGENTA) - data/csv/KNF_Rejestr_posrednikow_ubezpieczeniowych_pracownik_agenta.csv
    (@KNF_PRACOWNIK_AGENTA_SourceSystem_ID, N'PERSON', N'Imię', N'First_Name'),
    (@KNF_PRACOWNIK_AGENTA_SourceSystem_ID, N'PERSON', N'Nazwisko', N'Last_Name'),
    (@KNF_PRACOWNIK_AGENTA_SourceSystem_ID, N'PERSON', N'PESEL', N'PESEL'),
    (@KNF_PRACOWNIK_AGENTA_SourceSystem_ID, N'PERSON', N'Numer pracownika', N'Source_Record_ID'),

    -- PARTY (KNF_PRACOWNIK_AGENTA) - agent jako podmiot
    (@KNF_PRACOWNIK_AGENTA_SourceSystem_ID, N'PARTY', N'Nazwa agenta', N'Name'),
    (@KNF_PRACOWNIK_AGENTA_SourceSystem_ID, N'PARTY', N'Numer NIP agenta', N'Identifiers_JSON'),
    (@KNF_PRACOWNIK_AGENTA_SourceSystem_ID, N'PARTY', N'Numer KRS agenta', N'Identifiers_JSON'),
    (@KNF_PRACOWNIK_AGENTA_SourceSystem_ID, N'PARTY', N'Numer agenta', N'Register_Number'),
    (@KNF_PRACOWNIK_AGENTA_SourceSystem_ID, N'PARTY', N'Nazwa zakładu ubezpieczeń', N'Insurance_Company'),
    (@KNF_PRACOWNIK_AGENTA_SourceSystem_ID, N'PARTY', N'Data wpisu', N'Registration_Date'),
    (@KNF_PRACOWNIK_AGENTA_SourceSystem_ID, N'PARTY', N'Data zakończenia', N'Deregistration_Date')
) AS source ([SourceSystem_ID], [Entity_Type], [Source_Column_Name], [Canonical_Column_Name])
ON target.[SourceSystem_ID] = source.[SourceSystem_ID]
AND target.[Entity_Type] = source.[Entity_Type]
AND target.[Source_Column_Name] = source.[Source_Column_Name]
WHEN NOT MATCHED THEN
    INSERT ([SourceSystem_ID], [Entity_Type], [Source_Column_Name], [Canonical_Column_Name])
    VALUES (source.[SourceSystem_ID], source.[Entity_Type], source.[Source_Column_Name], source.[Canonical_Column_Name]);
GO

DECLARE @KNF_FIRMY_INWESTYCYJNE_SourceSystem_ID INT = (
    SELECT [SourceSystem_ID]
    FROM [meta].[SourceSystem]
    WHERE [SourceSystem_Code] = N'KNF_FIRMY_INWESTYCYJNE'
);

MERGE [meta].[ColumnMapping] AS target
USING (VALUES
    -- PARTY (KNF_FIRMY_INWESTYCYJNE) - data/csv/KNF_Rejestr_firm_inwestycyjnych.csv
    (@KNF_FIRMY_INWESTYCYJNE_SourceSystem_ID, N'PARTY', N'Firma lub nazwa', N'Name'),
    (@KNF_FIRMY_INWESTYCYJNE_SourceSystem_ID, N'PARTY', N'Adres siedziby', N'Street'),
    (@KNF_FIRMY_INWESTYCYJNE_SourceSystem_ID, N'PARTY', N'KRS', N'Identifiers_JSON'),
    (@KNF_FIRMY_INWESTYCYJNE_SourceSystem_ID, N'PARTY', N'NIP', N'Identifiers_JSON'),
    (@KNF_FIRMY_INWESTYCYJNE_SourceSystem_ID, N'PARTY', N'REGON', N'Identifiers_JSON'),
    (@KNF_FIRMY_INWESTYCYJNE_SourceSystem_ID, N'PARTY', N'Zakres czynności', N'Business_Scope'),
    (@KNF_FIRMY_INWESTYCYJNE_SourceSystem_ID, N'PARTY', N'Data zezwolenia', N'Registration_Date'),
    (@KNF_FIRMY_INWESTYCYJNE_SourceSystem_ID, N'PARTY', N'Numer decyzji', N'Decision_Number'),
    (@KNF_FIRMY_INWESTYCYJNE_SourceSystem_ID, N'PERSON', N'CzlonekZarzadu1_Imie', N'First_Name'),
    (@KNF_FIRMY_INWESTYCYJNE_SourceSystem_ID, N'PERSON', N'CzlonekZarzadu1_Nazwisko', N'Last_Name'),
    (@KNF_FIRMY_INWESTYCYJNE_SourceSystem_ID, N'PERSON', N'CzlonekZarzadu1_PESEL', N'PESEL')
) AS source ([SourceSystem_ID], [Entity_Type], [Source_Column_Name], [Canonical_Column_Name])
ON target.[SourceSystem_ID] = source.[SourceSystem_ID]
AND target.[Entity_Type] = source.[Entity_Type]
AND target.[Source_Column_Name] = source.[Source_Column_Name]
WHEN NOT MATCHED THEN
    INSERT ([SourceSystem_ID], [Entity_Type], [Source_Column_Name], [Canonical_Column_Name])
    VALUES (source.[SourceSystem_ID], source.[Entity_Type], source.[Source_Column_Name], source.[Canonical_Column_Name]);
GO

DECLARE @KNF_PIENIADZ_ELEKTRONICZNY_SourceSystem_ID INT = (
    SELECT [SourceSystem_ID]
    FROM [meta].[SourceSystem]
    WHERE [SourceSystem_Code] = N'KNF_PIENIADZ_ELEKTRONICZNY'
);

MERGE [meta].[ColumnMapping] AS target
USING (VALUES
    -- PARTY (KNF_PIENIADZ_ELEKTRONICZNY) - data/csv/KNF_Rejestr_dostawcow_i_wydawcow_pieniadza_elektronicznego.csv
    (@KNF_PIENIADZ_ELEKTRONICZNY_SourceSystem_ID, N'PARTY', N'Nazwa', N'Name'),
    (@KNF_PIENIADZ_ELEKTRONICZNY_SourceSystem_ID, N'PARTY', N'Typ podmiotu', N'Legal_Entity_Type'),
    (@KNF_PIENIADZ_ELEKTRONICZNY_SourceSystem_ID, N'PARTY', N'Data wpisu', N'Establishment_Date'),
    (@KNF_PIENIADZ_ELEKTRONICZNY_SourceSystem_ID, N'PARTY', N'Adres siedziby', N'Street'),
    (@KNF_PIENIADZ_ELEKTRONICZNY_SourceSystem_ID, N'PARTY', N'Siedziba', N'City'),
    (@KNF_PIENIADZ_ELEKTRONICZNY_SourceSystem_ID, N'PARTY', N'NIP', N'Identifiers_JSON'),
    (@KNF_PIENIADZ_ELEKTRONICZNY_SourceSystem_ID, N'PARTY', N'KRS', N'Identifiers_JSON'),
    (@KNF_PIENIADZ_ELEKTRONICZNY_SourceSystem_ID, N'PARTY', N'Numer UKNF', N'Identifiers_JSON'),
    (@KNF_PIENIADZ_ELEKTRONICZNY_SourceSystem_ID, N'PARTY', N'Status', N'Register_Status'),
    (@KNF_PIENIADZ_ELEKTRONICZNY_SourceSystem_ID, N'PARTY', N'Data wykreślenia', N'Deregistration_Date'),
    (@KNF_PIENIADZ_ELEKTRONICZNY_SourceSystem_ID, N'PARTY', N'Data decyzji', N'Decision_Date')
) AS source ([SourceSystem_ID], [Entity_Type], [Source_Column_Name], [Canonical_Column_Name])
ON target.[SourceSystem_ID] = source.[SourceSystem_ID]
AND target.[Entity_Type] = source.[Entity_Type]
AND target.[Source_Column_Name] = source.[Source_Column_Name]
WHEN NOT MATCHED THEN
    INSERT ([SourceSystem_ID], [Entity_Type], [Source_Column_Name], [Canonical_Column_Name])
    VALUES (source.[SourceSystem_ID], source.[Entity_Type], source.[Source_Column_Name], source.[Canonical_Column_Name]);
GO
