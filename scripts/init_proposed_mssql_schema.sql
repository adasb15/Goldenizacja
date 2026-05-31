IF DB_ID(N'goldenizacja') IS NULL
BEGIN
    CREATE DATABASE [goldenizacja];
END;
GO

USE [goldenizacja];
GO

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
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

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'gold')
    EXEC(N'CREATE SCHEMA [gold]');
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
        [Serial_Number_ID_Card_Normalized] NVARCHAR(30) NULL,
        [Serial_Number_Passport_Normalized] NVARCHAR(30) NULL,
        [First_Name_Normalized] NVARCHAR(100) NULL,
        [Second_Name_Normalized] NVARCHAR(100) NULL,
        [Last_Name_Normalized] NVARCHAR(100) NULL,
        [Family_Name_Normalized] NVARCHAR(100) NULL,
        [Full_Name_Normalized] NVARCHAR(255) NULL,
        [Birth_Date] DATE NULL,
        [Place_Of_Birth_Normalized] NVARCHAR(150) NULL,
        [Sex] BIT NULL,
        [Citizenship_Normalized] NVARCHAR(100) NULL,
        [Phone_Normalized] NVARCHAR(50) NULL,
        [Email_Normalized] NVARCHAR(255) NULL,
        [Street_Normalized] NVARCHAR(150) NULL,
        [Building_Number_Normalized] NVARCHAR(30) NULL,
        [Apartment_Number_Normalized] NVARCHAR(30) NULL,
        [City_Normalized] NVARCHAR(100) NULL,
        [Postal_City_Normalized] NVARCHAR(100) NULL,
        [Postal_Code_Normalized] NVARCHAR(20) NULL,
        [District_Normalized] NVARCHAR(100) NULL,
        [Province_Normalized] NVARCHAR(100) NULL,
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

IF COL_LENGTH(N'stg.Person_Preprocessed', N'Serial_Number_ID_Card_Normalized') IS NULL
    ALTER TABLE [stg].[Person_Preprocessed] ADD [Serial_Number_ID_Card_Normalized] NVARCHAR(30) NULL;
IF COL_LENGTH(N'stg.Person_Preprocessed', N'Serial_Number_Passport_Normalized') IS NULL
    ALTER TABLE [stg].[Person_Preprocessed] ADD [Serial_Number_Passport_Normalized] NVARCHAR(30) NULL;
IF COL_LENGTH(N'stg.Person_Preprocessed', N'Birth_Date') IS NULL
    ALTER TABLE [stg].[Person_Preprocessed] ADD [Birth_Date] DATE NULL;
IF COL_LENGTH(N'stg.Person_Preprocessed', N'Place_Of_Birth_Normalized') IS NULL
    ALTER TABLE [stg].[Person_Preprocessed] ADD [Place_Of_Birth_Normalized] NVARCHAR(150) NULL;
IF COL_LENGTH(N'stg.Person_Preprocessed', N'Sex') IS NULL
    ALTER TABLE [stg].[Person_Preprocessed] ADD [Sex] BIT NULL;
IF COL_LENGTH(N'stg.Person_Preprocessed', N'Citizenship_Normalized') IS NULL
    ALTER TABLE [stg].[Person_Preprocessed] ADD [Citizenship_Normalized] NVARCHAR(100) NULL;
IF COL_LENGTH(N'stg.Person_Preprocessed', N'Postal_City_Normalized') IS NULL
    ALTER TABLE [stg].[Person_Preprocessed] ADD [Postal_City_Normalized] NVARCHAR(100) NULL;
IF COL_LENGTH(N'stg.Person_Preprocessed', N'District_Normalized') IS NULL
    ALTER TABLE [stg].[Person_Preprocessed] ADD [District_Normalized] NVARCHAR(100) NULL;
IF COL_LENGTH(N'stg.Person_Preprocessed', N'Province_Normalized') IS NULL
    ALTER TABLE [stg].[Person_Preprocessed] ADD [Province_Normalized] NVARCHAR(100) NULL;
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
        [Registration_Country_Normalized] NVARCHAR(100) NULL,
        [Establishment_Date] DATE NULL,
        [NIP_Normalized] NVARCHAR(20) NULL,
        [REGON_Normalized] NVARCHAR(20) NULL,
        [KRS_Normalized] NVARCHAR(20) NULL,
        [LEI_Normalized] NVARCHAR(30) NULL,
        [Register_Status_Normalized] NVARCHAR(100) NULL,
        [Registration_Date] DATE NULL,
        [Deregistration_Date] DATE NULL,
        [Decision_Date] DATE NULL,
        [Decision_Number_Normalized] NVARCHAR(100) NULL,
        [Register_Number_Normalized] NVARCHAR(100) NULL,
        [Bank_Accounts_Normalized_JSON] NVARCHAR(MAX) NULL,
        [Has_Virtual_Accounts] BIT NULL,
        [Business_Scope_Normalized] NVARCHAR(MAX) NULL,
        [Ownership_Form_Normalized] NVARCHAR(150) NULL,
        [Municipality_Normalized] NVARCHAR(100) NULL,
        [Phone_Normalized] NVARCHAR(50) NULL,
        [Email_Normalized] NVARCHAR(255) NULL,
        [Website_Normalized] NVARCHAR(255) NULL,
        [Agent_Type_Normalized] NVARCHAR(100) NULL,
        [Insurance_Company_Normalized] NVARCHAR(255) NULL,
        [Related_Persons_Normalized_JSON] NVARCHAR(MAX) NULL,
        [Related_Parties_Normalized_JSON] NVARCHAR(MAX) NULL,
        [Registration_Status_Normalized] NVARCHAR(50) NULL,
        [Last_Update_Date] DATE NULL,
        [Next_Renewal_Date] DATE NULL,
        [Managing_LOU_Normalized] NVARCHAR(50) NULL,
        [Validation_Sources_Normalized] NVARCHAR(100) NULL,
        [Validation_Authority_ID_Normalized] NVARCHAR(500) NULL,
        [Validation_Authority_Entity_ID_Normalized] NVARCHAR(100) NULL,
        [Direct_Parent_LEI_Normalized] NVARCHAR(20) NULL,
        [Direct_Parent_Name_Normalized] NVARCHAR(255) NULL,
        [Direct_Parent_Relationship_Type_Normalized] NVARCHAR(100) NULL,
        [Direct_Parent_Relationship_Status_Normalized] NVARCHAR(50) NULL,
        [Direct_Parent_Relationship_Start_Date] DATE NULL,
        [Direct_Parent_Relationship_End_Date] DATE NULL,
        [Ultimate_Parent_LEI_Normalized] NVARCHAR(20) NULL,
        [Ultimate_Parent_Name_Normalized] NVARCHAR(255) NULL,
        [Ultimate_Parent_Relationship_Type_Normalized] NVARCHAR(100) NULL,
        [Ultimate_Parent_Relationship_Status_Normalized] NVARCHAR(50) NULL,
        [Ultimate_Parent_Relationship_Start_Date] DATE NULL,
        [Ultimate_Parent_Relationship_End_Date] DATE NULL,
        [Street_Normalized] NVARCHAR(150) NULL,
        [Building_Number_Normalized] NVARCHAR(30) NULL,
        [Apartment_Number_Normalized] NVARCHAR(30) NULL,
        [City_Normalized] NVARCHAR(100) NULL,
        [Postal_City_Normalized] NVARCHAR(100) NULL,
        [Postal_Code_Normalized] NVARCHAR(20) NULL,
        [District_Normalized] NVARCHAR(100) NULL,
        [Province_Normalized] NVARCHAR(100) NULL,
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

IF COL_LENGTH(N'stg.Party_Preprocessed', N'Registration_Country_Normalized') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Registration_Country_Normalized] NVARCHAR(100) NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Establishment_Date') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Establishment_Date] DATE NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Register_Status_Normalized') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Register_Status_Normalized] NVARCHAR(100) NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Registration_Date') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Registration_Date] DATE NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Deregistration_Date') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Deregistration_Date] DATE NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Decision_Date') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Decision_Date] DATE NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Decision_Number_Normalized') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Decision_Number_Normalized] NVARCHAR(100) NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Register_Number_Normalized') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Register_Number_Normalized] NVARCHAR(100) NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Bank_Accounts_Normalized_JSON') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Bank_Accounts_Normalized_JSON] NVARCHAR(MAX) NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Has_Virtual_Accounts') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Has_Virtual_Accounts] BIT NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Business_Scope_Normalized') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Business_Scope_Normalized] NVARCHAR(MAX) NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Ownership_Form_Normalized') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Ownership_Form_Normalized] NVARCHAR(150) NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Municipality_Normalized') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Municipality_Normalized] NVARCHAR(100) NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Agent_Type_Normalized') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Agent_Type_Normalized] NVARCHAR(100) NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Insurance_Company_Normalized') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Insurance_Company_Normalized] NVARCHAR(255) NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Related_Persons_Normalized_JSON') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Related_Persons_Normalized_JSON] NVARCHAR(MAX) NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Related_Parties_Normalized_JSON') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Related_Parties_Normalized_JSON] NVARCHAR(MAX) NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Registration_Status_Normalized') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Registration_Status_Normalized] NVARCHAR(50) NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Last_Update_Date') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Last_Update_Date] DATE NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Next_Renewal_Date') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Next_Renewal_Date] DATE NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Managing_LOU_Normalized') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Managing_LOU_Normalized] NVARCHAR(50) NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Validation_Sources_Normalized') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Validation_Sources_Normalized] NVARCHAR(100) NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Validation_Authority_ID_Normalized') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Validation_Authority_ID_Normalized] NVARCHAR(500) NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Validation_Authority_Entity_ID_Normalized') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Validation_Authority_Entity_ID_Normalized] NVARCHAR(100) NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Direct_Parent_LEI_Normalized') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Direct_Parent_LEI_Normalized] NVARCHAR(20) NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Direct_Parent_Name_Normalized') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Direct_Parent_Name_Normalized] NVARCHAR(255) NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Direct_Parent_Relationship_Type_Normalized') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Direct_Parent_Relationship_Type_Normalized] NVARCHAR(100) NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Direct_Parent_Relationship_Status_Normalized') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Direct_Parent_Relationship_Status_Normalized] NVARCHAR(50) NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Direct_Parent_Relationship_Start_Date') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Direct_Parent_Relationship_Start_Date] DATE NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Direct_Parent_Relationship_End_Date') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Direct_Parent_Relationship_End_Date] DATE NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Ultimate_Parent_LEI_Normalized') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Ultimate_Parent_LEI_Normalized] NVARCHAR(20) NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Ultimate_Parent_Name_Normalized') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Ultimate_Parent_Name_Normalized] NVARCHAR(255) NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Ultimate_Parent_Relationship_Type_Normalized') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Ultimate_Parent_Relationship_Type_Normalized] NVARCHAR(100) NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Ultimate_Parent_Relationship_Status_Normalized') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Ultimate_Parent_Relationship_Status_Normalized] NVARCHAR(50) NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Ultimate_Parent_Relationship_Start_Date') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Ultimate_Parent_Relationship_Start_Date] DATE NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Ultimate_Parent_Relationship_End_Date') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Ultimate_Parent_Relationship_End_Date] DATE NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Postal_City_Normalized') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Postal_City_Normalized] NVARCHAR(100) NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'District_Normalized') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [District_Normalized] NVARCHAR(100) NULL;
IF COL_LENGTH(N'stg.Party_Preprocessed', N'Province_Normalized') IS NULL
    ALTER TABLE [stg].[Party_Preprocessed] ADD [Province_Normalized] NVARCHAR(100) NULL;
GO

IF OBJECT_ID(N'[stg].[Match_Candidate_Levenshtein]', N'U') IS NULL
BEGIN
    CREATE TABLE [stg].[Match_Candidate_Levenshtein] (
        [Match_Candidate_Levenshtein_ID] BIGINT IDENTITY(1,1) NOT NULL,
        [Entity_Type] NVARCHAR(20) NOT NULL,
        [RawFile_ID] BIGINT NULL,
        [Left_Preprocessed_ID] BIGINT NOT NULL,
        [Right_Preprocessed_ID] BIGINT NOT NULL,
        [Left_Staging_ID] BIGINT NOT NULL,
        [Right_Staging_ID] BIGINT NOT NULL,
        [Left_RawFile_ID] BIGINT NOT NULL,
        [Right_RawFile_ID] BIGINT NOT NULL,
        [Left_Source_Record_ID] NVARCHAR(100) NULL,
        [Right_Source_Record_ID] NVARCHAR(100) NULL,
        [Score] FLOAT NOT NULL,
        [Decision] NVARCHAR(30) NOT NULL,
        [Strong_Match_Fields_JSON] NVARCHAR(MAX) NULL,
        [Conflict_Fields_JSON] NVARCHAR(MAX) NULL,
        [Created_At] DATETIME2(0) NOT NULL CONSTRAINT [DF_Match_Candidate_Levenshtein_Created_At] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [PK_Match_Candidate_Levenshtein] PRIMARY KEY CLUSTERED ([Match_Candidate_Levenshtein_ID]),
        CONSTRAINT [CK_Match_Candidate_Levenshtein_Entity_Type] CHECK ([Entity_Type] IN (N'PERSON', N'PARTY')),
        CONSTRAINT [CK_Match_Candidate_Levenshtein_Decision] CHECK ([Decision] IN (N'AUTO_MERGE', N'REVIEW', N'CANDIDATE')),
        CONSTRAINT [CK_Match_Candidate_Levenshtein_Score] CHECK ([Score] >= 0 AND [Score] <= 1),
        CONSTRAINT [CK_Match_Candidate_Levenshtein_Pair_Order] CHECK ([Left_Preprocessed_ID] < [Right_Preprocessed_ID]),
        CONSTRAINT [CK_Match_Candidate_Levenshtein_Strong_JSON] CHECK ([Strong_Match_Fields_JSON] IS NULL OR ISJSON([Strong_Match_Fields_JSON]) = 1),
        CONSTRAINT [CK_Match_Candidate_Levenshtein_Conflict_JSON] CHECK ([Conflict_Fields_JSON] IS NULL OR ISJSON([Conflict_Fields_JSON]) = 1)
    );
END;
GO

IF OBJECT_ID(N'[stg].[Match_Candidate_JaroWinkler]', N'U') IS NULL
BEGIN
    CREATE TABLE [stg].[Match_Candidate_JaroWinkler] (
        [Match_Candidate_JaroWinkler_ID] BIGINT IDENTITY(1,1) NOT NULL,
        [Levenshtein_Candidate_ID] BIGINT NOT NULL,
        [Entity_Type] NVARCHAR(20) NOT NULL,
        [RawFile_ID] BIGINT NULL,
        [Left_Preprocessed_ID] BIGINT NOT NULL,
        [Right_Preprocessed_ID] BIGINT NOT NULL,
        [Left_Staging_ID] BIGINT NOT NULL,
        [Right_Staging_ID] BIGINT NOT NULL,
        [Left_RawFile_ID] BIGINT NOT NULL,
        [Right_RawFile_ID] BIGINT NOT NULL,
        [Left_Source_Record_ID] NVARCHAR(100) NULL,
        [Right_Source_Record_ID] NVARCHAR(100) NULL,
        [Levenshtein_Score] FLOAT NOT NULL,
        [JaroWinkler_Score] FLOAT NOT NULL,
        [Decision] NVARCHAR(30) NOT NULL,
        [Strong_Match_Fields_JSON] NVARCHAR(MAX) NULL,
        [Conflict_Fields_JSON] NVARCHAR(MAX) NULL,
        [Text_Match_Fields_JSON] NVARCHAR(MAX) NULL,
        [Created_At] DATETIME2(0) NOT NULL CONSTRAINT [DF_Match_Candidate_JaroWinkler_Created_At] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [PK_Match_Candidate_JaroWinkler] PRIMARY KEY CLUSTERED ([Match_Candidate_JaroWinkler_ID]),
        CONSTRAINT [FK_Match_Candidate_JaroWinkler_Levenshtein] FOREIGN KEY ([Levenshtein_Candidate_ID])
            REFERENCES [stg].[Match_Candidate_Levenshtein] ([Match_Candidate_Levenshtein_ID]),
        CONSTRAINT [CK_Match_Candidate_JaroWinkler_Entity_Type] CHECK ([Entity_Type] IN (N'PERSON', N'PARTY')),
        CONSTRAINT [CK_Match_Candidate_JaroWinkler_Decision] CHECK ([Decision] IN (N'AUTO_MERGE', N'REVIEW', N'CANDIDATE')),
        CONSTRAINT [CK_Match_Candidate_JaroWinkler_Levenshtein_Score] CHECK ([Levenshtein_Score] >= 0 AND [Levenshtein_Score] <= 1),
        CONSTRAINT [CK_Match_Candidate_JaroWinkler_Score] CHECK ([JaroWinkler_Score] >= 0 AND [JaroWinkler_Score] <= 1),
        CONSTRAINT [CK_Match_Candidate_JaroWinkler_Pair_Order] CHECK ([Left_Preprocessed_ID] < [Right_Preprocessed_ID]),
        CONSTRAINT [CK_Match_Candidate_JaroWinkler_Strong_JSON] CHECK ([Strong_Match_Fields_JSON] IS NULL OR ISJSON([Strong_Match_Fields_JSON]) = 1),
        CONSTRAINT [CK_Match_Candidate_JaroWinkler_Conflict_JSON] CHECK ([Conflict_Fields_JSON] IS NULL OR ISJSON([Conflict_Fields_JSON]) = 1),
        CONSTRAINT [CK_Match_Candidate_JaroWinkler_Text_JSON] CHECK ([Text_Match_Fields_JSON] IS NULL OR ISJSON([Text_Match_Fields_JSON]) = 1)
    );
END;
GO

IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = N'FK_Match_Candidate_JaroWinkler_Levenshtein')
    ALTER TABLE [stg].[Match_Candidate_JaroWinkler] ADD CONSTRAINT [FK_Match_Candidate_JaroWinkler_Levenshtein]
        FOREIGN KEY ([Levenshtein_Candidate_ID]) REFERENCES [stg].[Match_Candidate_Levenshtein] ([Match_Candidate_Levenshtein_ID]);
GO

UPDATE [stg].[Match_Candidate_Levenshtein]
SET
    [Left_Preprocessed_ID] = [Right_Preprocessed_ID],
    [Right_Preprocessed_ID] = [Left_Preprocessed_ID],
    [Left_Staging_ID] = [Right_Staging_ID],
    [Right_Staging_ID] = [Left_Staging_ID],
    [Left_RawFile_ID] = [Right_RawFile_ID],
    [Right_RawFile_ID] = [Left_RawFile_ID],
    [Left_Source_Record_ID] = [Right_Source_Record_ID],
    [Right_Source_Record_ID] = [Left_Source_Record_ID]
WHERE [Left_Preprocessed_ID] > [Right_Preprocessed_ID];
GO

UPDATE [stg].[Match_Candidate_JaroWinkler]
SET
    [Left_Preprocessed_ID] = [Right_Preprocessed_ID],
    [Right_Preprocessed_ID] = [Left_Preprocessed_ID],
    [Left_Staging_ID] = [Right_Staging_ID],
    [Right_Staging_ID] = [Left_Staging_ID],
    [Left_RawFile_ID] = [Right_RawFile_ID],
    [Right_RawFile_ID] = [Left_RawFile_ID],
    [Left_Source_Record_ID] = [Right_Source_Record_ID],
    [Right_Source_Record_ID] = [Left_Source_Record_ID]
WHERE [Left_Preprocessed_ID] > [Right_Preprocessed_ID];
GO

DELETE FROM [stg].[Match_Candidate_JaroWinkler]
WHERE [Left_Preprocessed_ID] = [Right_Preprocessed_ID];
GO

DELETE FROM [stg].[Match_Candidate_Levenshtein]
WHERE [Left_Preprocessed_ID] = [Right_Preprocessed_ID];
GO

;WITH [Ranked_JaroWinkler] AS (
    SELECT
        [Match_Candidate_JaroWinkler_ID],
        ROW_NUMBER() OVER (
            PARTITION BY [RawFile_ID], [Entity_Type], [Left_Preprocessed_ID], [Right_Preprocessed_ID]
            ORDER BY [Match_Candidate_JaroWinkler_ID]
        ) AS [Pair_Row_Number]
    FROM [stg].[Match_Candidate_JaroWinkler]
)
DELETE FROM [Ranked_JaroWinkler]
WHERE [Pair_Row_Number] > 1;
GO

;WITH [Ranked_Levenshtein] AS (
    SELECT
        [Match_Candidate_Levenshtein_ID],
        MIN([Match_Candidate_Levenshtein_ID]) OVER (
            PARTITION BY [RawFile_ID], [Entity_Type], [Left_Preprocessed_ID], [Right_Preprocessed_ID]
        ) AS [Canonical_Candidate_ID]
    FROM [stg].[Match_Candidate_Levenshtein]
)
UPDATE [JaroWinkler]
SET [Levenshtein_Candidate_ID] = [Levenshtein].[Canonical_Candidate_ID]
FROM [stg].[Match_Candidate_JaroWinkler] AS [JaroWinkler]
INNER JOIN [Ranked_Levenshtein] AS [Levenshtein]
    ON [Levenshtein].[Match_Candidate_Levenshtein_ID] = [JaroWinkler].[Levenshtein_Candidate_ID]
WHERE [Levenshtein].[Match_Candidate_Levenshtein_ID] <> [Levenshtein].[Canonical_Candidate_ID];
GO

;WITH [Ranked_Levenshtein] AS (
    SELECT
        [Match_Candidate_Levenshtein_ID],
        ROW_NUMBER() OVER (
            PARTITION BY [RawFile_ID], [Entity_Type], [Left_Preprocessed_ID], [Right_Preprocessed_ID]
            ORDER BY [Match_Candidate_Levenshtein_ID]
        ) AS [Pair_Row_Number]
    FROM [stg].[Match_Candidate_Levenshtein]
)
DELETE FROM [Ranked_Levenshtein]
WHERE [Pair_Row_Number] > 1;
GO

IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = N'CK_Match_Candidate_Levenshtein_Pair_Order')
    ALTER TABLE [stg].[Match_Candidate_Levenshtein] ADD CONSTRAINT [CK_Match_Candidate_Levenshtein_Pair_Order]
        CHECK ([Left_Preprocessed_ID] < [Right_Preprocessed_ID]);
IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = N'CK_Match_Candidate_JaroWinkler_Pair_Order')
    ALTER TABLE [stg].[Match_Candidate_JaroWinkler] ADD CONSTRAINT [CK_Match_Candidate_JaroWinkler_Pair_Order]
        CHECK ([Left_Preprocessed_ID] < [Right_Preprocessed_ID]);
GO

IF OBJECT_ID(N'[stg].[Entity_Group]', N'U') IS NULL
BEGIN
    CREATE TABLE [stg].[Entity_Group] (
        [Entity_Group_ID] BIGINT IDENTITY(1,1) NOT NULL,
        [Entity_Type] NVARCHAR(20) NOT NULL,
        [Group_Key] NVARCHAR(64) NOT NULL,
        [Created_At] DATETIME2(0) NOT NULL CONSTRAINT [DF_Entity_Group_Created_At] DEFAULT SYSUTCDATETIME(),
        [Updated_At] DATETIME2(0) NOT NULL CONSTRAINT [DF_Entity_Group_Updated_At] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [PK_Entity_Group] PRIMARY KEY CLUSTERED ([Entity_Group_ID]),
        CONSTRAINT [UQ_Entity_Group_Type_Key] UNIQUE ([Entity_Type], [Group_Key]),
        CONSTRAINT [UQ_Entity_Group_ID_Type] UNIQUE ([Entity_Group_ID], [Entity_Type]),
        CONSTRAINT [CK_Entity_Group_Entity_Type] CHECK ([Entity_Type] IN (N'PERSON', N'PARTY'))
    );
END;
GO

IF OBJECT_ID(N'[stg].[Entity_Group_Member]', N'U') IS NULL
BEGIN
    CREATE TABLE [stg].[Entity_Group_Member] (
        [Entity_Group_Member_ID] BIGINT IDENTITY(1,1) NOT NULL,
        [Entity_Group_ID] BIGINT NOT NULL,
        [Entity_Type] NVARCHAR(20) NOT NULL,
        [Preprocessed_ID] BIGINT NOT NULL,
        [Person_Preprocessed_ID] BIGINT NULL,
        [Party_Preprocessed_ID] BIGINT NULL,
        [Created_At] DATETIME2(0) NOT NULL CONSTRAINT [DF_Entity_Group_Member_Created_At] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [PK_Entity_Group_Member] PRIMARY KEY CLUSTERED ([Entity_Group_Member_ID]),
        CONSTRAINT [FK_Entity_Group_Member_Group_Type] FOREIGN KEY ([Entity_Group_ID], [Entity_Type])
            REFERENCES [stg].[Entity_Group] ([Entity_Group_ID], [Entity_Type]) ON DELETE CASCADE,
        CONSTRAINT [FK_Entity_Group_Member_Person_Preprocessed] FOREIGN KEY ([Person_Preprocessed_ID])
            REFERENCES [stg].[Person_Preprocessed] ([Preprocessed_ID]),
        CONSTRAINT [FK_Entity_Group_Member_Party_Preprocessed] FOREIGN KEY ([Party_Preprocessed_ID])
            REFERENCES [stg].[Party_Preprocessed] ([Preprocessed_ID]),
        CONSTRAINT [UQ_Entity_Group_Member_Type_Preprocessed] UNIQUE ([Entity_Type], [Preprocessed_ID]),
        CONSTRAINT [CK_Entity_Group_Member_Entity_Type] CHECK ([Entity_Type] IN (N'PERSON', N'PARTY')),
        CONSTRAINT [CK_Entity_Group_Member_Preprocessed_Reference] CHECK (
            ([Entity_Type] = N'PERSON' AND [Person_Preprocessed_ID] = [Preprocessed_ID] AND [Party_Preprocessed_ID] IS NULL)
            OR ([Entity_Type] = N'PARTY' AND [Party_Preprocessed_ID] = [Preprocessed_ID] AND [Person_Preprocessed_ID] IS NULL)
        )
    );
END;
GO

IF NOT EXISTS (SELECT 1 FROM sys.key_constraints WHERE name = N'UQ_Entity_Group_ID_Type')
    ALTER TABLE [stg].[Entity_Group] ADD CONSTRAINT [UQ_Entity_Group_ID_Type]
        UNIQUE ([Entity_Group_ID], [Entity_Type]);
IF NOT EXISTS (SELECT 1 FROM sys.key_constraints WHERE name = N'UQ_Entity_Group_Type_Key')
    ALTER TABLE [stg].[Entity_Group] ADD CONSTRAINT [UQ_Entity_Group_Type_Key]
        UNIQUE ([Entity_Type], [Group_Key]);
IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = N'CK_Entity_Group_Entity_Type')
    ALTER TABLE [stg].[Entity_Group] ADD CONSTRAINT [CK_Entity_Group_Entity_Type]
        CHECK ([Entity_Type] IN (N'PERSON', N'PARTY'));
DECLARE @DropOldEntityGroupMemberForeignKeys NVARCHAR(MAX) = N'';
SELECT @DropOldEntityGroupMemberForeignKeys +=
    N'ALTER TABLE [stg].[Entity_Group_Member] DROP CONSTRAINT ' + QUOTENAME([name]) + N';'
FROM sys.foreign_keys
WHERE [parent_object_id] = OBJECT_ID(N'[stg].[Entity_Group_Member]')
  AND [referenced_object_id] = OBJECT_ID(N'[stg].[Entity_Group]')
  AND [name] <> N'FK_Entity_Group_Member_Group_Type';
IF @DropOldEntityGroupMemberForeignKeys <> N''
    EXEC sp_executesql @DropOldEntityGroupMemberForeignKeys;
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = N'FK_Entity_Group_Member_Group_Type')
    ALTER TABLE [stg].[Entity_Group_Member] ADD CONSTRAINT [FK_Entity_Group_Member_Group_Type]
        FOREIGN KEY ([Entity_Group_ID], [Entity_Type]) REFERENCES [stg].[Entity_Group] ([Entity_Group_ID], [Entity_Type]) ON DELETE CASCADE;
GO

IF COL_LENGTH(N'stg.Entity_Group_Member', N'Person_Preprocessed_ID') IS NULL
    ALTER TABLE [stg].[Entity_Group_Member] ADD [Person_Preprocessed_ID] BIGINT NULL;
IF COL_LENGTH(N'stg.Entity_Group_Member', N'Party_Preprocessed_ID') IS NULL
    ALTER TABLE [stg].[Entity_Group_Member] ADD [Party_Preprocessed_ID] BIGINT NULL;
GO

UPDATE [stg].[Entity_Group_Member]
SET
    [Person_Preprocessed_ID] = CASE WHEN [Entity_Type] = N'PERSON' THEN [Preprocessed_ID] ELSE NULL END,
    [Party_Preprocessed_ID] = CASE WHEN [Entity_Type] = N'PARTY' THEN [Preprocessed_ID] ELSE NULL END;
GO

IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = N'FK_Entity_Group_Member_Person_Preprocessed')
    ALTER TABLE [stg].[Entity_Group_Member] ADD CONSTRAINT [FK_Entity_Group_Member_Person_Preprocessed]
        FOREIGN KEY ([Person_Preprocessed_ID]) REFERENCES [stg].[Person_Preprocessed] ([Preprocessed_ID]);
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = N'FK_Entity_Group_Member_Party_Preprocessed')
    ALTER TABLE [stg].[Entity_Group_Member] ADD CONSTRAINT [FK_Entity_Group_Member_Party_Preprocessed]
        FOREIGN KEY ([Party_Preprocessed_ID]) REFERENCES [stg].[Party_Preprocessed] ([Preprocessed_ID]);
IF NOT EXISTS (SELECT 1 FROM sys.key_constraints WHERE name = N'UQ_Entity_Group_Member_Type_Preprocessed')
    ALTER TABLE [stg].[Entity_Group_Member] ADD CONSTRAINT [UQ_Entity_Group_Member_Type_Preprocessed]
        UNIQUE ([Entity_Type], [Preprocessed_ID]);
IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = N'CK_Entity_Group_Member_Entity_Type')
    ALTER TABLE [stg].[Entity_Group_Member] ADD CONSTRAINT [CK_Entity_Group_Member_Entity_Type]
        CHECK ([Entity_Type] IN (N'PERSON', N'PARTY'));
IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = N'CK_Entity_Group_Member_Preprocessed_Reference')
    ALTER TABLE [stg].[Entity_Group_Member] ADD CONSTRAINT [CK_Entity_Group_Member_Preprocessed_Reference] CHECK (
        ([Entity_Type] = N'PERSON' AND [Person_Preprocessed_ID] = [Preprocessed_ID] AND [Party_Preprocessed_ID] IS NULL)
        OR ([Entity_Type] = N'PARTY' AND [Party_Preprocessed_ID] = [Preprocessed_ID] AND [Person_Preprocessed_ID] IS NULL)
    );
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

IF OBJECT_ID(N'[gold].[DimAddress]', N'U') IS NULL
BEGIN
    CREATE TABLE [gold].[DimAddress] (
        [Address_ID] BIGINT IDENTITY(1,1) NOT NULL,
        [Street] NVARCHAR(100) NULL,
        [Building_Number] NVARCHAR(20) NULL,
        [Apartment_Number] NVARCHAR(20) NULL,
        [City] NVARCHAR(50) NULL,
        [Postal_City] NVARCHAR(50) NULL,
        [Postal_Code] NVARCHAR(20) NULL,
        [District] NVARCHAR(50) NULL,
        [Province] NVARCHAR(50) NULL,
        [Country] NVARCHAR(50) NULL,
        [Created_At] DATETIME2(0) NOT NULL CONSTRAINT [DF_DimAddress_Created_At] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [PK_DimAddress] PRIMARY KEY CLUSTERED ([Address_ID])
    );
END;
GO

IF OBJECT_ID(N'[gold].[DimAddressType]', N'U') IS NULL
BEGIN
    CREATE TABLE [gold].[DimAddressType] (
        [AddressType_ID] INT IDENTITY(1,1) NOT NULL,
        [AddressType_Name] NVARCHAR(50) NOT NULL,
        CONSTRAINT [PK_DimAddressType] PRIMARY KEY CLUSTERED ([AddressType_ID]),
        CONSTRAINT [UQ_DimAddressType_Name] UNIQUE ([AddressType_Name])
    );
END;
GO

IF OBJECT_ID(N'[gold].[DimIdentityType]', N'U') IS NULL
BEGIN
    CREATE TABLE [gold].[DimIdentityType] (
        [IdentityType_ID] INT IDENTITY(1,1) NOT NULL,
        [IdentityType_Name] NVARCHAR(50) NOT NULL,
        CONSTRAINT [PK_DimIdentityType] PRIMARY KEY CLUSTERED ([IdentityType_ID]),
        CONSTRAINT [UQ_DimIdentityType_Name] UNIQUE ([IdentityType_Name])
    );
END;
GO

IF OBJECT_ID(N'[gold].[DimParty]', N'U') IS NULL
BEGIN
    CREATE TABLE [gold].[DimParty] (
        [Party_ID] BIGINT IDENTITY(1,1) NOT NULL,
        [Name] NVARCHAR(255) NOT NULL,
        [Short_Name] NVARCHAR(255) NULL,
        [Legal_Entity_Type] NVARCHAR(100) NULL,
        [Registration_Country] NVARCHAR(50) NULL,
        [Establishment_Date] DATE NULL,
        [Created_At] DATETIME2(0) NOT NULL CONSTRAINT [DF_DimParty_Created_At] DEFAULT SYSUTCDATETIME(),
        [Updated_At] DATETIME2(0) NULL,
        CONSTRAINT [PK_DimParty] PRIMARY KEY CLUSTERED ([Party_ID])
    );
END;
GO

IF OBJECT_ID(N'[gold].[DimPartyRelationshipType]', N'U') IS NULL
BEGIN
    CREATE TABLE [gold].[DimPartyRelationshipType] (
        [RelationshipType_ID] INT IDENTITY(1,1) NOT NULL,
        [Relationship_Name] NVARCHAR(50) NOT NULL,
        CONSTRAINT [PK_DimPartyRelationshipType] PRIMARY KEY CLUSTERED ([RelationshipType_ID]),
        CONSTRAINT [UQ_DimPartyRelationshipType_Name] UNIQUE ([Relationship_Name])
    );
END;
GO

IF OBJECT_ID(N'[gold].[DimPerson]', N'U') IS NULL
BEGIN
    CREATE TABLE [gold].[DimPerson] (
        [Person_ID] BIGINT IDENTITY(1,1) NOT NULL,
        [PESEL] NVARCHAR(11) NULL,
        [Serial_Number_ID_Card] NVARCHAR(20) NULL,
        [Serial_Number_Passport] NVARCHAR(20) NULL,
        [First_Name] NVARCHAR(50) NULL,
        [Second_Name] NVARCHAR(50) NULL,
        [Last_Name] NVARCHAR(50) NULL,
        [Family_Name] NVARCHAR(50) NULL,
        [Birth_Date] DATE NULL,
        [Place_Of_Birth] NVARCHAR(100) NULL,
        [Sex] BIT NULL,
        [Citizenship] NVARCHAR(50) NULL,
        [Phone_Number] NVARCHAR(20) NULL,
        [Email_Address] NVARCHAR(100) NULL,
        [Created_At] DATETIME2(0) NOT NULL CONSTRAINT [DF_DimPerson_Created_At] DEFAULT SYSUTCDATETIME(),
        [Updated_At] DATETIME2(0) NULL,
        CONSTRAINT [PK_DimPerson] PRIMARY KEY CLUSTERED ([Person_ID])
    );
END;
GO

IF OBJECT_ID(N'[gold].[DimRegister]', N'U') IS NULL
BEGIN
    CREATE TABLE [gold].[DimRegister] (
        [Register_ID] INT IDENTITY(1,1) NOT NULL,
        [Register_Name] NVARCHAR(100) NOT NULL,
        CONSTRAINT [PK_DimRegister] PRIMARY KEY CLUSTERED ([Register_ID]),
        CONSTRAINT [UQ_DimRegister_Name] UNIQUE ([Register_Name])
    );
END;
GO

IF OBJECT_ID(N'[gold].[DimRegisterStatus]', N'U') IS NULL
BEGIN
    CREATE TABLE [gold].[DimRegisterStatus] (
        [RegisterStatus_ID] INT IDENTITY(1,1) NOT NULL,
        [Status_Name] NVARCHAR(50) NOT NULL,
        CONSTRAINT [PK_DimRegisterStatus] PRIMARY KEY CLUSTERED ([RegisterStatus_ID]),
        CONSTRAINT [UQ_DimRegisterStatus_Name] UNIQUE ([Status_Name])
    );
END;
GO

IF OBJECT_ID(N'[gold].[DimRoleType]', N'U') IS NULL
BEGIN
    CREATE TABLE [gold].[DimRoleType] (
        [RoleType_ID] INT IDENTITY(1,1) NOT NULL,
        [Role_Name] NVARCHAR(50) NOT NULL,
        CONSTRAINT [PK_DimRoleType] PRIMARY KEY CLUSTERED ([RoleType_ID]),
        CONSTRAINT [UQ_DimRoleType_Name] UNIQUE ([Role_Name])
    );
END;
GO

IF OBJECT_ID(N'[gold].[FactlessPartyAddress]', N'U') IS NULL
BEGIN
    CREATE TABLE [gold].[FactlessPartyAddress] (
        [PartyAddress_ID] BIGINT IDENTITY(1,1) NOT NULL,
        [Party_ID] BIGINT NOT NULL,
        [Address_ID] BIGINT NOT NULL,
        [AddressType_ID] INT NOT NULL,
        [Valid_From] DATE NULL,
        [Valid_To] DATE NULL,
        CONSTRAINT [PK_FactlessPartyAddress] PRIMARY KEY CLUSTERED ([PartyAddress_ID]),
        CONSTRAINT [FK_FactlessPartyAddress_Party] FOREIGN KEY ([Party_ID]) REFERENCES [gold].[DimParty] ([Party_ID]),
        CONSTRAINT [FK_FactlessPartyAddress_Address] FOREIGN KEY ([Address_ID]) REFERENCES [gold].[DimAddress] ([Address_ID]),
        CONSTRAINT [FK_FactlessPartyAddress_AddressType] FOREIGN KEY ([AddressType_ID]) REFERENCES [gold].[DimAddressType] ([AddressType_ID]),
        CONSTRAINT [CK_FactlessPartyAddress_Dates] CHECK ([Valid_To] IS NULL OR [Valid_From] IS NULL OR [Valid_To] >= [Valid_From])
    );
END;
GO

IF OBJECT_ID(N'[gold].[FactlessPartyIdentities]', N'U') IS NULL
BEGIN
    CREATE TABLE [gold].[FactlessPartyIdentities] (
        [PartyIdentity_ID] BIGINT IDENTITY(1,1) NOT NULL,
        [Party_ID] BIGINT NOT NULL,
        [IdentityType_ID] INT NOT NULL,
        [Identity_Value] NVARCHAR(100) NOT NULL,
        [Is_Valid] BIT NULL,
        [Match_Confidence] DECIMAL(5,4) NULL,
        [Valid_From] DATE NULL,
        [Valid_To] DATE NULL,
        CONSTRAINT [PK_FactlessPartyIdentities] PRIMARY KEY CLUSTERED ([PartyIdentity_ID]),
        CONSTRAINT [FK_FactlessPartyIdentities_Party] FOREIGN KEY ([Party_ID]) REFERENCES [gold].[DimParty] ([Party_ID]),
        CONSTRAINT [FK_FactlessPartyIdentities_IdentityType] FOREIGN KEY ([IdentityType_ID]) REFERENCES [gold].[DimIdentityType] ([IdentityType_ID]),
        CONSTRAINT [UQ_FactlessPartyIdentities_Type_Value] UNIQUE ([IdentityType_ID], [Identity_Value]),
        CONSTRAINT [CK_FactlessPartyIdentities_Match_Confidence] CHECK ([Match_Confidence] IS NULL OR ([Match_Confidence] >= 0 AND [Match_Confidence] <= 1)),
        CONSTRAINT [CK_FactlessPartyIdentities_Dates] CHECK ([Valid_To] IS NULL OR [Valid_From] IS NULL OR [Valid_To] >= [Valid_From])
    );
END;
GO

IF OBJECT_ID(N'[gold].[FactlessPartyRegisterEntry]', N'U') IS NULL
BEGIN
    CREATE TABLE [gold].[FactlessPartyRegisterEntry] (
        [PartyRegisterEntry_ID] BIGINT IDENTITY(1,1) NOT NULL,
        [Party_ID] BIGINT NOT NULL,
        [Register_ID] INT NOT NULL,
        [RegisterStatus_ID] INT NOT NULL,
        [Registration_Date] DATE NULL,
        [Deregistration_Date] DATE NULL,
        CONSTRAINT [PK_FactlessPartyRegisterEntry] PRIMARY KEY CLUSTERED ([PartyRegisterEntry_ID]),
        CONSTRAINT [FK_FactlessPartyRegisterEntry_Party] FOREIGN KEY ([Party_ID]) REFERENCES [gold].[DimParty] ([Party_ID]),
        CONSTRAINT [FK_FactlessPartyRegisterEntry_Register] FOREIGN KEY ([Register_ID]) REFERENCES [gold].[DimRegister] ([Register_ID]),
        CONSTRAINT [FK_FactlessPartyRegisterEntry_Status] FOREIGN KEY ([RegisterStatus_ID]) REFERENCES [gold].[DimRegisterStatus] ([RegisterStatus_ID]),
        CONSTRAINT [CK_FactlessPartyRegisterEntry_Dates] CHECK ([Deregistration_Date] IS NULL OR [Registration_Date] IS NULL OR [Deregistration_Date] >= [Registration_Date])
    );
END;
GO

IF OBJECT_ID(N'[gold].[FactlessPartyRelationship]', N'U') IS NULL
BEGIN
    CREATE TABLE [gold].[FactlessPartyRelationship] (
        [PartyRelationship_ID] BIGINT IDENTITY(1,1) NOT NULL,
        [Parent_Party_ID] BIGINT NOT NULL,
        [Child_Party_ID] BIGINT NOT NULL,
        [RelationshipType_ID] INT NOT NULL,
        [Valid_From] DATE NULL,
        [Valid_To] DATE NULL,
        CONSTRAINT [PK_FactlessPartyRelationship] PRIMARY KEY CLUSTERED ([PartyRelationship_ID]),
        CONSTRAINT [FK_FactlessPartyRelationship_Parent] FOREIGN KEY ([Parent_Party_ID]) REFERENCES [gold].[DimParty] ([Party_ID]),
        CONSTRAINT [FK_FactlessPartyRelationship_Child] FOREIGN KEY ([Child_Party_ID]) REFERENCES [gold].[DimParty] ([Party_ID]),
        CONSTRAINT [FK_FactlessPartyRelationship_Type] FOREIGN KEY ([RelationshipType_ID]) REFERENCES [gold].[DimPartyRelationshipType] ([RelationshipType_ID]),
        CONSTRAINT [CK_FactlessPartyRelationship_No_Self] CHECK ([Parent_Party_ID] <> [Child_Party_ID]),
        CONSTRAINT [CK_FactlessPartyRelationship_Dates] CHECK ([Valid_To] IS NULL OR [Valid_From] IS NULL OR [Valid_To] >= [Valid_From])
    );
END;
GO

IF OBJECT_ID(N'[gold].[FactlessPersonAddress]', N'U') IS NULL
BEGIN
    CREATE TABLE [gold].[FactlessPersonAddress] (
        [PersonAddress_ID] BIGINT IDENTITY(1,1) NOT NULL,
        [Person_ID] BIGINT NOT NULL,
        [Address_ID] BIGINT NOT NULL,
        [AddressType_ID] INT NOT NULL,
        [Valid_From] DATE NULL,
        [Valid_To] DATE NULL,
        CONSTRAINT [PK_FactlessPersonAddress] PRIMARY KEY CLUSTERED ([PersonAddress_ID]),
        CONSTRAINT [FK_FactlessPersonAddress_Person] FOREIGN KEY ([Person_ID]) REFERENCES [gold].[DimPerson] ([Person_ID]),
        CONSTRAINT [FK_FactlessPersonAddress_Address] FOREIGN KEY ([Address_ID]) REFERENCES [gold].[DimAddress] ([Address_ID]),
        CONSTRAINT [FK_FactlessPersonAddress_AddressType] FOREIGN KEY ([AddressType_ID]) REFERENCES [gold].[DimAddressType] ([AddressType_ID]),
        CONSTRAINT [CK_FactlessPersonAddress_Dates] CHECK ([Valid_To] IS NULL OR [Valid_From] IS NULL OR [Valid_To] >= [Valid_From])
    );
END;
GO

IF OBJECT_ID(N'[gold].[FactlessPersonPartyRole]', N'U') IS NULL
BEGIN
    CREATE TABLE [gold].[FactlessPersonPartyRole] (
        [PersonPartyRole_ID] BIGINT IDENTITY(1,1) NOT NULL,
        [Person_ID] BIGINT NOT NULL,
        [Party_ID] BIGINT NOT NULL,
        [RoleType_ID] INT NOT NULL,
        [Valid_From] DATE NULL,
        [Valid_To] DATE NULL,
        CONSTRAINT [PK_FactlessPersonPartyRole] PRIMARY KEY CLUSTERED ([PersonPartyRole_ID]),
        CONSTRAINT [FK_FactlessPersonPartyRole_Person] FOREIGN KEY ([Person_ID]) REFERENCES [gold].[DimPerson] ([Person_ID]),
        CONSTRAINT [FK_FactlessPersonPartyRole_Party] FOREIGN KEY ([Party_ID]) REFERENCES [gold].[DimParty] ([Party_ID]),
        CONSTRAINT [FK_FactlessPersonPartyRole_RoleType] FOREIGN KEY ([RoleType_ID]) REFERENCES [gold].[DimRoleType] ([RoleType_ID]),
        CONSTRAINT [CK_FactlessPersonPartyRole_Dates] CHECK ([Valid_To] IS NULL OR [Valid_From] IS NULL OR [Valid_To] >= [Valid_From])
    );
END;
GO

IF OBJECT_ID(N'[gold].[EntityChangeLog]', N'U') IS NULL
BEGIN
    CREATE TABLE [gold].[EntityChangeLog] (
        [Change_ID] BIGINT IDENTITY(1,1) NOT NULL,
        [Entity_Type] NVARCHAR(20) NOT NULL,
        [DimPerson_ID] BIGINT NULL,
        [DimParty_ID] BIGINT NULL,
        [DimAddress_ID] BIGINT NULL,
        [PartyIdentity_ID] BIGINT NULL,
        [Attribute_Name] NVARCHAR(100) NOT NULL,
        [Old_Value] NVARCHAR(4000) NULL,
        [New_Value] NVARCHAR(4000) NULL,
        [Change_Date] DATETIME2(0) NOT NULL CONSTRAINT [DF_EntityChangeLog_Change_Date] DEFAULT SYSUTCDATETIME(),
        [ImportBatch_ID] BIGINT NULL,
        CONSTRAINT [PK_EntityChangeLog] PRIMARY KEY CLUSTERED ([Change_ID]),
        CONSTRAINT [FK_EntityChangeLog_Person] FOREIGN KEY ([DimPerson_ID]) REFERENCES [gold].[DimPerson] ([Person_ID]),
        CONSTRAINT [FK_EntityChangeLog_Party] FOREIGN KEY ([DimParty_ID]) REFERENCES [gold].[DimParty] ([Party_ID]),
        CONSTRAINT [FK_EntityChangeLog_Address] FOREIGN KEY ([DimAddress_ID]) REFERENCES [gold].[DimAddress] ([Address_ID]),
        CONSTRAINT [FK_EntityChangeLog_PartyIdentity] FOREIGN KEY ([PartyIdentity_ID]) REFERENCES [gold].[FactlessPartyIdentities] ([PartyIdentity_ID]),
        CONSTRAINT [FK_EntityChangeLog_ImportBatch] FOREIGN KEY ([ImportBatch_ID]) REFERENCES [meta].[ImportBatch] ([ImportBatch_ID]),
        CONSTRAINT [CK_EntityChangeLog_Entity_Type] CHECK ([Entity_Type] IN (N'PERSON', N'PARTY', N'ADDRESS', N'PARTY_IDENTITY')),
        CONSTRAINT [CK_EntityChangeLog_Entity_Ref] CHECK (
            ([Entity_Type] = N'PERSON' AND [DimPerson_ID] IS NOT NULL AND [DimParty_ID] IS NULL AND [DimAddress_ID] IS NULL AND [PartyIdentity_ID] IS NULL) OR
            ([Entity_Type] = N'PARTY' AND [DimPerson_ID] IS NULL AND [DimParty_ID] IS NOT NULL AND [DimAddress_ID] IS NULL AND [PartyIdentity_ID] IS NULL) OR
            ([Entity_Type] = N'ADDRESS' AND [DimPerson_ID] IS NULL AND [DimParty_ID] IS NULL AND [DimAddress_ID] IS NOT NULL AND [PartyIdentity_ID] IS NULL) OR
            ([Entity_Type] = N'PARTY_IDENTITY' AND [DimPerson_ID] IS NULL AND [DimParty_ID] IS NULL AND [DimAddress_ID] IS NULL AND [PartyIdentity_ID] IS NOT NULL)
        )
    );
END;
GO

IF OBJECT_ID(N'[gold].[GoldenPersonLineage]', N'U') IS NULL
BEGIN
    CREATE TABLE [gold].[GoldenPersonLineage] (
        [Lineage_ID] BIGINT IDENTITY(1,1) NOT NULL,
        [DimPerson_ID] BIGINT NOT NULL,
        [Attribute_Name] NVARCHAR(100) NOT NULL,
        [SourceSystem_ID] INT NOT NULL,
        [Source_Record_ID] NVARCHAR(100) NULL,
        [ImportBatch_ID] BIGINT NOT NULL,
        [Selection_Rule] NVARCHAR(100) NULL,
        [Trust_Score] DECIMAL(5,4) NULL,
        [Quality_Score] DECIMAL(5,4) NULL,
        [Validation_Status] NVARCHAR(30) NULL,
        [Recorded_At] DATETIME2(0) NOT NULL CONSTRAINT [DF_GoldenPersonLineage_Recorded_At] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [PK_GoldenPersonLineage] PRIMARY KEY CLUSTERED ([Lineage_ID]),
        CONSTRAINT [FK_GoldenPersonLineage_Person] FOREIGN KEY ([DimPerson_ID]) REFERENCES [gold].[DimPerson] ([Person_ID]),
        CONSTRAINT [FK_GoldenPersonLineage_SourceSystem] FOREIGN KEY ([SourceSystem_ID]) REFERENCES [meta].[SourceSystem] ([SourceSystem_ID]),
        CONSTRAINT [FK_GoldenPersonLineage_ImportBatch] FOREIGN KEY ([ImportBatch_ID]) REFERENCES [meta].[ImportBatch] ([ImportBatch_ID]),
        CONSTRAINT [CK_GoldenPersonLineage_Trust_Score] CHECK ([Trust_Score] IS NULL OR ([Trust_Score] >= 0 AND [Trust_Score] <= 1)),
        CONSTRAINT [CK_GoldenPersonLineage_Quality_Score] CHECK ([Quality_Score] IS NULL OR ([Quality_Score] >= 0 AND [Quality_Score] <= 1))
    );
END;
GO

IF OBJECT_ID(N'[gold].[GoldenPartyLineage]', N'U') IS NULL
BEGIN
    CREATE TABLE [gold].[GoldenPartyLineage] (
        [Lineage_ID] BIGINT IDENTITY(1,1) NOT NULL,
        [DimParty_ID] BIGINT NOT NULL,
        [Attribute_Name] NVARCHAR(100) NOT NULL,
        [SourceSystem_ID] INT NOT NULL,
        [Source_Record_ID] NVARCHAR(100) NULL,
        [ImportBatch_ID] BIGINT NOT NULL,
        [Selection_Rule] NVARCHAR(100) NULL,
        [Trust_Score] DECIMAL(5,4) NULL,
        [Quality_Score] DECIMAL(5,4) NULL,
        [Validation_Status] NVARCHAR(30) NULL,
        [Recorded_At] DATETIME2(0) NOT NULL CONSTRAINT [DF_GoldenPartyLineage_Recorded_At] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [PK_GoldenPartyLineage] PRIMARY KEY CLUSTERED ([Lineage_ID]),
        CONSTRAINT [FK_GoldenPartyLineage_Party] FOREIGN KEY ([DimParty_ID]) REFERENCES [gold].[DimParty] ([Party_ID]),
        CONSTRAINT [FK_GoldenPartyLineage_SourceSystem] FOREIGN KEY ([SourceSystem_ID]) REFERENCES [meta].[SourceSystem] ([SourceSystem_ID]),
        CONSTRAINT [FK_GoldenPartyLineage_ImportBatch] FOREIGN KEY ([ImportBatch_ID]) REFERENCES [meta].[ImportBatch] ([ImportBatch_ID]),
        CONSTRAINT [CK_GoldenPartyLineage_Trust_Score] CHECK ([Trust_Score] IS NULL OR ([Trust_Score] >= 0 AND [Trust_Score] <= 1)),
        CONSTRAINT [CK_GoldenPartyLineage_Quality_Score] CHECK ([Quality_Score] IS NULL OR ([Quality_Score] >= 0 AND [Quality_Score] <= 1))
    );
END;
GO

IF OBJECT_ID(N'[gold].[GoldenAddressLineage]', N'U') IS NULL
BEGIN
    CREATE TABLE [gold].[GoldenAddressLineage] (
        [Lineage_ID] BIGINT IDENTITY(1,1) NOT NULL,
        [DimAddress_ID] BIGINT NOT NULL,
        [Attribute_Name] NVARCHAR(100) NOT NULL,
        [SourceSystem_ID] INT NOT NULL,
        [Source_Record_ID] NVARCHAR(100) NULL,
        [ImportBatch_ID] BIGINT NOT NULL,
        [Selection_Rule] NVARCHAR(100) NULL,
        [Trust_Score] DECIMAL(5,4) NULL,
        [Quality_Score] DECIMAL(5,4) NULL,
        [Validation_Status] NVARCHAR(30) NULL,
        [Recorded_At] DATETIME2(0) NOT NULL CONSTRAINT [DF_GoldenAddressLineage_Recorded_At] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [PK_GoldenAddressLineage] PRIMARY KEY CLUSTERED ([Lineage_ID]),
        CONSTRAINT [FK_GoldenAddressLineage_Address] FOREIGN KEY ([DimAddress_ID]) REFERENCES [gold].[DimAddress] ([Address_ID]),
        CONSTRAINT [FK_GoldenAddressLineage_SourceSystem] FOREIGN KEY ([SourceSystem_ID]) REFERENCES [meta].[SourceSystem] ([SourceSystem_ID]),
        CONSTRAINT [FK_GoldenAddressLineage_ImportBatch] FOREIGN KEY ([ImportBatch_ID]) REFERENCES [meta].[ImportBatch] ([ImportBatch_ID]),
        CONSTRAINT [CK_GoldenAddressLineage_Trust_Score] CHECK ([Trust_Score] IS NULL OR ([Trust_Score] >= 0 AND [Trust_Score] <= 1)),
        CONSTRAINT [CK_GoldenAddressLineage_Quality_Score] CHECK ([Quality_Score] IS NULL OR ([Quality_Score] >= 0 AND [Quality_Score] <= 1))
    );
END;
GO

IF OBJECT_ID(N'[gold].[GoldenPartyIdentityLineage]', N'U') IS NULL
BEGIN
    CREATE TABLE [gold].[GoldenPartyIdentityLineage] (
        [Lineage_ID] BIGINT IDENTITY(1,1) NOT NULL,
        [PartyIdentity_ID] BIGINT NOT NULL,
        [Attribute_Name] NVARCHAR(100) NOT NULL,
        [SourceSystem_ID] INT NOT NULL,
        [Source_Record_ID] NVARCHAR(100) NULL,
        [ImportBatch_ID] BIGINT NOT NULL,
        [Selection_Rule] NVARCHAR(100) NULL,
        [Trust_Score] DECIMAL(5,4) NULL,
        [Quality_Score] DECIMAL(5,4) NULL,
        [Validation_Status] NVARCHAR(30) NULL,
        [Recorded_At] DATETIME2(0) NOT NULL CONSTRAINT [DF_GoldenPartyIdentityLineage_Recorded_At] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [PK_GoldenPartyIdentityLineage] PRIMARY KEY CLUSTERED ([Lineage_ID]),
        CONSTRAINT [FK_GoldenPartyIdentityLineage_Identity] FOREIGN KEY ([PartyIdentity_ID]) REFERENCES [gold].[FactlessPartyIdentities] ([PartyIdentity_ID]),
        CONSTRAINT [FK_GoldenPartyIdentityLineage_SourceSystem] FOREIGN KEY ([SourceSystem_ID]) REFERENCES [meta].[SourceSystem] ([SourceSystem_ID]),
        CONSTRAINT [FK_GoldenPartyIdentityLineage_ImportBatch] FOREIGN KEY ([ImportBatch_ID]) REFERENCES [meta].[ImportBatch] ([ImportBatch_ID]),
        CONSTRAINT [CK_GoldenPartyIdentityLineage_Trust_Score] CHECK ([Trust_Score] IS NULL OR ([Trust_Score] >= 0 AND [Trust_Score] <= 1)),
        CONSTRAINT [CK_GoldenPartyIdentityLineage_Quality_Score] CHECK ([Quality_Score] IS NULL OR ([Quality_Score] >= 0 AND [Quality_Score] <= 1))
    );
END;
GO

IF OBJECT_ID(N'[gold].[PartyAddressLineage]', N'U') IS NULL
BEGIN
    CREATE TABLE [gold].[PartyAddressLineage] (
        [RelationshipLineage_ID] BIGINT IDENTITY(1,1) NOT NULL,
        [PartyAddress_ID] BIGINT NOT NULL,
        [SourceSystem_ID] INT NOT NULL,
        [Source_Record_ID] NVARCHAR(100) NULL,
        [ImportBatch_ID] BIGINT NOT NULL,
        [Selection_Rule] NVARCHAR(100) NULL,
        [Trust_Score] DECIMAL(5,4) NULL,
        [Quality_Score] DECIMAL(5,4) NULL,
        [Validation_Status] NVARCHAR(30) NULL,
        [Recorded_At] DATETIME2(0) NOT NULL CONSTRAINT [DF_PartyAddressLineage_Recorded_At] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [PK_PartyAddressLineage] PRIMARY KEY CLUSTERED ([RelationshipLineage_ID]),
        CONSTRAINT [FK_PartyAddressLineage_PartyAddress] FOREIGN KEY ([PartyAddress_ID]) REFERENCES [gold].[FactlessPartyAddress] ([PartyAddress_ID]),
        CONSTRAINT [FK_PartyAddressLineage_SourceSystem] FOREIGN KEY ([SourceSystem_ID]) REFERENCES [meta].[SourceSystem] ([SourceSystem_ID]),
        CONSTRAINT [FK_PartyAddressLineage_ImportBatch] FOREIGN KEY ([ImportBatch_ID]) REFERENCES [meta].[ImportBatch] ([ImportBatch_ID]),
        CONSTRAINT [CK_PartyAddressLineage_Trust_Score] CHECK ([Trust_Score] IS NULL OR ([Trust_Score] >= 0 AND [Trust_Score] <= 1)),
        CONSTRAINT [CK_PartyAddressLineage_Quality_Score] CHECK ([Quality_Score] IS NULL OR ([Quality_Score] >= 0 AND [Quality_Score] <= 1))
    );
END;
GO

IF OBJECT_ID(N'[gold].[PersonAddressLineage]', N'U') IS NULL
BEGIN
    CREATE TABLE [gold].[PersonAddressLineage] (
        [RelationshipLineage_ID] BIGINT IDENTITY(1,1) NOT NULL,
        [PersonAddress_ID] BIGINT NOT NULL,
        [SourceSystem_ID] INT NOT NULL,
        [Source_Record_ID] NVARCHAR(100) NULL,
        [ImportBatch_ID] BIGINT NOT NULL,
        [Selection_Rule] NVARCHAR(100) NULL,
        [Trust_Score] DECIMAL(5,4) NULL,
        [Quality_Score] DECIMAL(5,4) NULL,
        [Validation_Status] NVARCHAR(30) NULL,
        [Recorded_At] DATETIME2(0) NOT NULL CONSTRAINT [DF_PersonAddressLineage_Recorded_At] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [PK_PersonAddressLineage] PRIMARY KEY CLUSTERED ([RelationshipLineage_ID]),
        CONSTRAINT [FK_PersonAddressLineage_PersonAddress] FOREIGN KEY ([PersonAddress_ID]) REFERENCES [gold].[FactlessPersonAddress] ([PersonAddress_ID]),
        CONSTRAINT [FK_PersonAddressLineage_SourceSystem] FOREIGN KEY ([SourceSystem_ID]) REFERENCES [meta].[SourceSystem] ([SourceSystem_ID]),
        CONSTRAINT [FK_PersonAddressLineage_ImportBatch] FOREIGN KEY ([ImportBatch_ID]) REFERENCES [meta].[ImportBatch] ([ImportBatch_ID]),
        CONSTRAINT [CK_PersonAddressLineage_Trust_Score] CHECK ([Trust_Score] IS NULL OR ([Trust_Score] >= 0 AND [Trust_Score] <= 1)),
        CONSTRAINT [CK_PersonAddressLineage_Quality_Score] CHECK ([Quality_Score] IS NULL OR ([Quality_Score] >= 0 AND [Quality_Score] <= 1))
    );
END;
GO

IF OBJECT_ID(N'[gold].[PersonPartyRoleLineage]', N'U') IS NULL
BEGIN
    CREATE TABLE [gold].[PersonPartyRoleLineage] (
        [RelationshipLineage_ID] BIGINT IDENTITY(1,1) NOT NULL,
        [PersonPartyRole_ID] BIGINT NOT NULL,
        [SourceSystem_ID] INT NOT NULL,
        [Source_Record_ID] NVARCHAR(100) NULL,
        [ImportBatch_ID] BIGINT NOT NULL,
        [Selection_Rule] NVARCHAR(100) NULL,
        [Trust_Score] DECIMAL(5,4) NULL,
        [Quality_Score] DECIMAL(5,4) NULL,
        [Validation_Status] NVARCHAR(30) NULL,
        [Recorded_At] DATETIME2(0) NOT NULL CONSTRAINT [DF_PersonPartyRoleLineage_Recorded_At] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [PK_PersonPartyRoleLineage] PRIMARY KEY CLUSTERED ([RelationshipLineage_ID]),
        CONSTRAINT [FK_PersonPartyRoleLineage_Role] FOREIGN KEY ([PersonPartyRole_ID]) REFERENCES [gold].[FactlessPersonPartyRole] ([PersonPartyRole_ID]),
        CONSTRAINT [FK_PersonPartyRoleLineage_SourceSystem] FOREIGN KEY ([SourceSystem_ID]) REFERENCES [meta].[SourceSystem] ([SourceSystem_ID]),
        CONSTRAINT [FK_PersonPartyRoleLineage_ImportBatch] FOREIGN KEY ([ImportBatch_ID]) REFERENCES [meta].[ImportBatch] ([ImportBatch_ID]),
        CONSTRAINT [CK_PersonPartyRoleLineage_Trust_Score] CHECK ([Trust_Score] IS NULL OR ([Trust_Score] >= 0 AND [Trust_Score] <= 1)),
        CONSTRAINT [CK_PersonPartyRoleLineage_Quality_Score] CHECK ([Quality_Score] IS NULL OR ([Quality_Score] >= 0 AND [Quality_Score] <= 1))
    );
END;
GO

IF OBJECT_ID(N'[gold].[PartyRegisterEntryLineage]', N'U') IS NULL
BEGIN
    CREATE TABLE [gold].[PartyRegisterEntryLineage] (
        [RelationshipLineage_ID] BIGINT IDENTITY(1,1) NOT NULL,
        [PartyRegisterEntry_ID] BIGINT NOT NULL,
        [SourceSystem_ID] INT NOT NULL,
        [Source_Record_ID] NVARCHAR(100) NULL,
        [ImportBatch_ID] BIGINT NOT NULL,
        [Selection_Rule] NVARCHAR(100) NULL,
        [Trust_Score] DECIMAL(5,4) NULL,
        [Quality_Score] DECIMAL(5,4) NULL,
        [Validation_Status] NVARCHAR(30) NULL,
        [Recorded_At] DATETIME2(0) NOT NULL CONSTRAINT [DF_PartyRegisterEntryLineage_Recorded_At] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [PK_PartyRegisterEntryLineage] PRIMARY KEY CLUSTERED ([RelationshipLineage_ID]),
        CONSTRAINT [FK_PartyRegisterEntryLineage_Entry] FOREIGN KEY ([PartyRegisterEntry_ID]) REFERENCES [gold].[FactlessPartyRegisterEntry] ([PartyRegisterEntry_ID]),
        CONSTRAINT [FK_PartyRegisterEntryLineage_SourceSystem] FOREIGN KEY ([SourceSystem_ID]) REFERENCES [meta].[SourceSystem] ([SourceSystem_ID]),
        CONSTRAINT [FK_PartyRegisterEntryLineage_ImportBatch] FOREIGN KEY ([ImportBatch_ID]) REFERENCES [meta].[ImportBatch] ([ImportBatch_ID]),
        CONSTRAINT [CK_PartyRegisterEntryLineage_Trust_Score] CHECK ([Trust_Score] IS NULL OR ([Trust_Score] >= 0 AND [Trust_Score] <= 1)),
        CONSTRAINT [CK_PartyRegisterEntryLineage_Quality_Score] CHECK ([Quality_Score] IS NULL OR ([Quality_Score] >= 0 AND [Quality_Score] <= 1))
    );
END;
GO

IF OBJECT_ID(N'[gold].[PartyRelationshipLineage]', N'U') IS NULL
BEGIN
    CREATE TABLE [gold].[PartyRelationshipLineage] (
        [RelationshipLineage_ID] BIGINT IDENTITY(1,1) NOT NULL,
        [PartyRelationship_ID] BIGINT NOT NULL,
        [SourceSystem_ID] INT NOT NULL,
        [Source_Record_ID] NVARCHAR(100) NULL,
        [ImportBatch_ID] BIGINT NOT NULL,
        [Selection_Rule] NVARCHAR(100) NULL,
        [Trust_Score] DECIMAL(5,4) NULL,
        [Quality_Score] DECIMAL(5,4) NULL,
        [Validation_Status] NVARCHAR(30) NULL,
        [Recorded_At] DATETIME2(0) NOT NULL CONSTRAINT [DF_PartyRelationshipLineage_Recorded_At] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [PK_PartyRelationshipLineage] PRIMARY KEY CLUSTERED ([RelationshipLineage_ID]),
        CONSTRAINT [FK_PartyRelationshipLineage_Relationship] FOREIGN KEY ([PartyRelationship_ID]) REFERENCES [gold].[FactlessPartyRelationship] ([PartyRelationship_ID]),
        CONSTRAINT [FK_PartyRelationshipLineage_SourceSystem] FOREIGN KEY ([SourceSystem_ID]) REFERENCES [meta].[SourceSystem] ([SourceSystem_ID]),
        CONSTRAINT [FK_PartyRelationshipLineage_ImportBatch] FOREIGN KEY ([ImportBatch_ID]) REFERENCES [meta].[ImportBatch] ([ImportBatch_ID]),
        CONSTRAINT [CK_PartyRelationshipLineage_Trust_Score] CHECK ([Trust_Score] IS NULL OR ([Trust_Score] >= 0 AND [Trust_Score] <= 1)),
        CONSTRAINT [CK_PartyRelationshipLineage_Quality_Score] CHECK ([Quality_Score] IS NULL OR ([Quality_Score] >= 0 AND [Quality_Score] <= 1))
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

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Person_Preprocessed_IDCard' AND object_id = OBJECT_ID(N'[stg].[Person_Preprocessed]'))
    CREATE INDEX [IX_Person_Preprocessed_IDCard] ON [stg].[Person_Preprocessed] ([Serial_Number_ID_Card_Normalized]) WHERE [Serial_Number_ID_Card_Normalized] IS NOT NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Person_Preprocessed_Passport' AND object_id = OBJECT_ID(N'[stg].[Person_Preprocessed]'))
    CREATE INDEX [IX_Person_Preprocessed_Passport] ON [stg].[Person_Preprocessed] ([Serial_Number_Passport_Normalized]) WHERE [Serial_Number_Passport_Normalized] IS NOT NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Person_Preprocessed_Email' AND object_id = OBJECT_ID(N'[stg].[Person_Preprocessed]'))
    CREATE INDEX [IX_Person_Preprocessed_Email] ON [stg].[Person_Preprocessed] ([Email_Normalized]) WHERE [Email_Normalized] IS NOT NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Person_Preprocessed_Phone' AND object_id = OBJECT_ID(N'[stg].[Person_Preprocessed]'))
    CREATE INDEX [IX_Person_Preprocessed_Phone] ON [stg].[Person_Preprocessed] ([Phone_Normalized]) WHERE [Phone_Normalized] IS NOT NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Person_Preprocessed_Birth_Last' AND object_id = OBJECT_ID(N'[stg].[Person_Preprocessed]'))
    CREATE INDEX [IX_Person_Preprocessed_Birth_Last] ON [stg].[Person_Preprocessed] ([Birth_Date], [Last_Name_Normalized]) WHERE [Birth_Date] IS NOT NULL AND [Last_Name_Normalized] IS NOT NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Person_Preprocessed_Birth_First_Last' AND object_id = OBJECT_ID(N'[stg].[Person_Preprocessed]'))
    CREATE INDEX [IX_Person_Preprocessed_Birth_First_Last] ON [stg].[Person_Preprocessed] ([Birth_Date], [First_Name_Normalized], [Last_Name_Normalized]) WHERE [Birth_Date] IS NOT NULL AND [First_Name_Normalized] IS NOT NULL AND [Last_Name_Normalized] IS NOT NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Person_Preprocessed_Birth_Place' AND object_id = OBJECT_ID(N'[stg].[Person_Preprocessed]'))
    CREATE INDEX [IX_Person_Preprocessed_Birth_Place] ON [stg].[Person_Preprocessed] ([Birth_Date], [Place_Of_Birth_Normalized]) WHERE [Birth_Date] IS NOT NULL AND [Place_Of_Birth_Normalized] IS NOT NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Person_Preprocessed_Postal_Last' AND object_id = OBJECT_ID(N'[stg].[Person_Preprocessed]'))
    CREATE INDEX [IX_Person_Preprocessed_Postal_Last] ON [stg].[Person_Preprocessed] ([Postal_Code_Normalized], [Last_Name_Normalized]) WHERE [Postal_Code_Normalized] IS NOT NULL AND [Last_Name_Normalized] IS NOT NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Party_Preprocessed_RawFile_ID' AND object_id = OBJECT_ID(N'[stg].[Party_Preprocessed]'))
    CREATE INDEX [IX_Party_Preprocessed_RawFile_ID] ON [stg].[Party_Preprocessed] ([RawFile_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Party_Preprocessed_Match' AND object_id = OBJECT_ID(N'[stg].[Party_Preprocessed]'))
    CREATE INDEX [IX_Party_Preprocessed_Match] ON [stg].[Party_Preprocessed] ([NIP_Normalized], [REGON_Normalized], [KRS_Normalized]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Party_Preprocessed_LEI' AND object_id = OBJECT_ID(N'[stg].[Party_Preprocessed]'))
    CREATE INDEX [IX_Party_Preprocessed_LEI] ON [stg].[Party_Preprocessed] ([LEI_Normalized]) WHERE [LEI_Normalized] IS NOT NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Party_Preprocessed_Decision_Number' AND object_id = OBJECT_ID(N'[stg].[Party_Preprocessed]'))
    CREATE INDEX [IX_Party_Preprocessed_Decision_Number] ON [stg].[Party_Preprocessed] ([Decision_Number_Normalized]) WHERE [Decision_Number_Normalized] IS NOT NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Party_Preprocessed_Register_Number' AND object_id = OBJECT_ID(N'[stg].[Party_Preprocessed]'))
    CREATE INDEX [IX_Party_Preprocessed_Register_Number] ON [stg].[Party_Preprocessed] ([Register_Number_Normalized]) WHERE [Register_Number_Normalized] IS NOT NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Party_Preprocessed_Validation_Entity' AND object_id = OBJECT_ID(N'[stg].[Party_Preprocessed]'))
    CREATE INDEX [IX_Party_Preprocessed_Validation_Entity] ON [stg].[Party_Preprocessed] ([Validation_Authority_Entity_ID_Normalized]) WHERE [Validation_Authority_Entity_ID_Normalized] IS NOT NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Party_Preprocessed_Website' AND object_id = OBJECT_ID(N'[stg].[Party_Preprocessed]'))
    CREATE INDEX [IX_Party_Preprocessed_Website] ON [stg].[Party_Preprocessed] ([Website_Normalized]) WHERE [Website_Normalized] IS NOT NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Party_Preprocessed_Email' AND object_id = OBJECT_ID(N'[stg].[Party_Preprocessed]'))
    CREATE INDEX [IX_Party_Preprocessed_Email] ON [stg].[Party_Preprocessed] ([Email_Normalized]) WHERE [Email_Normalized] IS NOT NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Party_Preprocessed_Phone' AND object_id = OBJECT_ID(N'[stg].[Party_Preprocessed]'))
    CREATE INDEX [IX_Party_Preprocessed_Phone] ON [stg].[Party_Preprocessed] ([Phone_Normalized]) WHERE [Phone_Normalized] IS NOT NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Party_Preprocessed_Name_City' AND object_id = OBJECT_ID(N'[stg].[Party_Preprocessed]'))
    CREATE INDEX [IX_Party_Preprocessed_Name_City] ON [stg].[Party_Preprocessed] ([Name_Normalized], [City_Normalized]) WHERE [Name_Normalized] IS NOT NULL AND [City_Normalized] IS NOT NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Party_Preprocessed_Name_Postal' AND object_id = OBJECT_ID(N'[stg].[Party_Preprocessed]'))
    CREATE INDEX [IX_Party_Preprocessed_Name_Postal] ON [stg].[Party_Preprocessed] ([Name_Normalized], [Postal_Code_Normalized]) WHERE [Name_Normalized] IS NOT NULL AND [Postal_Code_Normalized] IS NOT NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Party_Preprocessed_Name_Country' AND object_id = OBJECT_ID(N'[stg].[Party_Preprocessed]'))
    CREATE INDEX [IX_Party_Preprocessed_Name_Country] ON [stg].[Party_Preprocessed] ([Name_Normalized], [Country_Normalized]) WHERE [Name_Normalized] IS NOT NULL AND [Country_Normalized] IS NOT NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Party_Preprocessed_Short_Country' AND object_id = OBJECT_ID(N'[stg].[Party_Preprocessed]'))
    CREATE INDEX [IX_Party_Preprocessed_Short_Country] ON [stg].[Party_Preprocessed] ([Short_Name_Normalized], [Country_Normalized]) WHERE [Short_Name_Normalized] IS NOT NULL AND [Country_Normalized] IS NOT NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Party_Preprocessed_Legal_Name' AND object_id = OBJECT_ID(N'[stg].[Party_Preprocessed]'))
    CREATE INDEX [IX_Party_Preprocessed_Legal_Name] ON [stg].[Party_Preprocessed] ([Legal_Entity_Type_Normalized], [Name_Normalized]) WHERE [Legal_Entity_Type_Normalized] IS NOT NULL AND [Name_Normalized] IS NOT NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Match_Candidate_Levenshtein_RawFile_Entity' AND object_id = OBJECT_ID(N'[stg].[Match_Candidate_Levenshtein]'))
    CREATE INDEX [IX_Match_Candidate_Levenshtein_RawFile_Entity] ON [stg].[Match_Candidate_Levenshtein] ([RawFile_ID], [Entity_Type]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Match_Candidate_Levenshtein_Decision_Score' AND object_id = OBJECT_ID(N'[stg].[Match_Candidate_Levenshtein]'))
    CREATE INDEX [IX_Match_Candidate_Levenshtein_Decision_Score] ON [stg].[Match_Candidate_Levenshtein] ([Decision], [Score]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Match_Candidate_Levenshtein_Left_Right' AND object_id = OBJECT_ID(N'[stg].[Match_Candidate_Levenshtein]'))
    CREATE INDEX [IX_Match_Candidate_Levenshtein_Left_Right] ON [stg].[Match_Candidate_Levenshtein] ([Left_Preprocessed_ID], [Right_Preprocessed_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'UX_Match_Candidate_Levenshtein_RawFile_Entity_Pair' AND object_id = OBJECT_ID(N'[stg].[Match_Candidate_Levenshtein]'))
    CREATE UNIQUE INDEX [UX_Match_Candidate_Levenshtein_RawFile_Entity_Pair] ON [stg].[Match_Candidate_Levenshtein] ([RawFile_ID], [Entity_Type], [Left_Preprocessed_ID], [Right_Preprocessed_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Match_Candidate_JaroWinkler_RawFile_Entity' AND object_id = OBJECT_ID(N'[stg].[Match_Candidate_JaroWinkler]'))
    CREATE INDEX [IX_Match_Candidate_JaroWinkler_RawFile_Entity] ON [stg].[Match_Candidate_JaroWinkler] ([RawFile_ID], [Entity_Type]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Match_Candidate_JaroWinkler_Decision_Score' AND object_id = OBJECT_ID(N'[stg].[Match_Candidate_JaroWinkler]'))
    CREATE INDEX [IX_Match_Candidate_JaroWinkler_Decision_Score] ON [stg].[Match_Candidate_JaroWinkler] ([Decision], [JaroWinkler_Score]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Match_Candidate_JaroWinkler_Levenshtein' AND object_id = OBJECT_ID(N'[stg].[Match_Candidate_JaroWinkler]'))
    CREATE INDEX [IX_Match_Candidate_JaroWinkler_Levenshtein] ON [stg].[Match_Candidate_JaroWinkler] ([Levenshtein_Candidate_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'UX_Match_Candidate_JaroWinkler_RawFile_Entity_Pair' AND object_id = OBJECT_ID(N'[stg].[Match_Candidate_JaroWinkler]'))
    CREATE UNIQUE INDEX [UX_Match_Candidate_JaroWinkler_RawFile_Entity_Pair] ON [stg].[Match_Candidate_JaroWinkler] ([RawFile_ID], [Entity_Type], [Left_Preprocessed_ID], [Right_Preprocessed_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Entity_Group_Member_Group' AND object_id = OBJECT_ID(N'[stg].[Entity_Group_Member]'))
    CREATE INDEX [IX_Entity_Group_Member_Group] ON [stg].[Entity_Group_Member] ([Entity_Group_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Validation_Result_RawFile_Entity' AND object_id = OBJECT_ID(N'[stg].[Validation_Result]'))
    CREATE INDEX [IX_Validation_Result_RawFile_Entity] ON [stg].[Validation_Result] ([RawFile_ID], [Entity_Type]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Validation_Result_Status' AND object_id = OBJECT_ID(N'[stg].[Validation_Result]'))
    CREATE INDEX [IX_Validation_Result_Status] ON [stg].[Validation_Result] ([Status], [Rule_Code]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_DimPerson_PESEL' AND object_id = OBJECT_ID(N'[gold].[DimPerson]'))
    CREATE UNIQUE INDEX [IX_DimPerson_PESEL] ON [gold].[DimPerson] ([PESEL]) WHERE [PESEL] IS NOT NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_DimPerson_Email' AND object_id = OBJECT_ID(N'[gold].[DimPerson]'))
    CREATE UNIQUE INDEX [IX_DimPerson_Email] ON [gold].[DimPerson] ([Email_Address]) WHERE [Email_Address] IS NOT NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_DimPerson_IDCard' AND object_id = OBJECT_ID(N'[gold].[DimPerson]'))
    CREATE UNIQUE INDEX [IX_DimPerson_IDCard] ON [gold].[DimPerson] ([Serial_Number_ID_Card]) WHERE [Serial_Number_ID_Card] IS NOT NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_DimPerson_Passport' AND object_id = OBJECT_ID(N'[gold].[DimPerson]'))
    CREATE UNIQUE INDEX [IX_DimPerson_Passport] ON [gold].[DimPerson] ([Serial_Number_Passport]) WHERE [Serial_Number_Passport] IS NOT NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_DimPerson_Phone' AND object_id = OBJECT_ID(N'[gold].[DimPerson]'))
    CREATE UNIQUE INDEX [IX_DimPerson_Phone] ON [gold].[DimPerson] ([Phone_Number]) WHERE [Phone_Number] IS NOT NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_DimParty_Name' AND object_id = OBJECT_ID(N'[gold].[DimParty]'))
    CREATE INDEX [IX_DimParty_Name] ON [gold].[DimParty] ([Name]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_EntityChangeLog_Entity' AND object_id = OBJECT_ID(N'[gold].[EntityChangeLog]'))
    CREATE INDEX [IX_EntityChangeLog_Entity] ON [gold].[EntityChangeLog] ([Entity_Type], [DimPerson_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_EntityChangeLog_ChangeDate' AND object_id = OBJECT_ID(N'[gold].[EntityChangeLog]'))
    CREATE INDEX [IX_EntityChangeLog_ChangeDate] ON [gold].[EntityChangeLog] ([Change_Date]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_EntityChangeLog_Party' AND object_id = OBJECT_ID(N'[gold].[EntityChangeLog]'))
    CREATE INDEX [IX_EntityChangeLog_Party] ON [gold].[EntityChangeLog] ([DimParty_ID]) WHERE [DimParty_ID] IS NOT NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_EntityChangeLog_Address' AND object_id = OBJECT_ID(N'[gold].[EntityChangeLog]'))
    CREATE INDEX [IX_EntityChangeLog_Address] ON [gold].[EntityChangeLog] ([DimAddress_ID]) WHERE [DimAddress_ID] IS NOT NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_EntityChangeLog_PartyIdentity' AND object_id = OBJECT_ID(N'[gold].[EntityChangeLog]'))
    CREATE INDEX [IX_EntityChangeLog_PartyIdentity] ON [gold].[EntityChangeLog] ([PartyIdentity_ID]) WHERE [PartyIdentity_ID] IS NOT NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_EntityChangeLog_ImportBatch' AND object_id = OBJECT_ID(N'[gold].[EntityChangeLog]'))
    CREATE INDEX [IX_EntityChangeLog_ImportBatch] ON [gold].[EntityChangeLog] ([ImportBatch_ID]) WHERE [ImportBatch_ID] IS NOT NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_FactlessPartyAddress_Party' AND object_id = OBJECT_ID(N'[gold].[FactlessPartyAddress]'))
    CREATE INDEX [IX_FactlessPartyAddress_Party] ON [gold].[FactlessPartyAddress] ([Party_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_FactlessPartyAddress_Address' AND object_id = OBJECT_ID(N'[gold].[FactlessPartyAddress]'))
    CREATE INDEX [IX_FactlessPartyAddress_Address] ON [gold].[FactlessPartyAddress] ([Address_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_FactlessPartyIdentities_Party' AND object_id = OBJECT_ID(N'[gold].[FactlessPartyIdentities]'))
    CREATE INDEX [IX_FactlessPartyIdentities_Party] ON [gold].[FactlessPartyIdentities] ([Party_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_FactlessPartyIdentities_Type' AND object_id = OBJECT_ID(N'[gold].[FactlessPartyIdentities]'))
    CREATE INDEX [IX_FactlessPartyIdentities_Type] ON [gold].[FactlessPartyIdentities] ([IdentityType_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_FactlessPartyIdentities_Value' AND object_id = OBJECT_ID(N'[gold].[FactlessPartyIdentities]'))
    CREATE INDEX [IX_FactlessPartyIdentities_Value] ON [gold].[FactlessPartyIdentities] ([Identity_Value]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_FactlessPartyRegisterEntry_Party' AND object_id = OBJECT_ID(N'[gold].[FactlessPartyRegisterEntry]'))
    CREATE INDEX [IX_FactlessPartyRegisterEntry_Party] ON [gold].[FactlessPartyRegisterEntry] ([Party_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_FactlessPartyRegisterEntry_Register' AND object_id = OBJECT_ID(N'[gold].[FactlessPartyRegisterEntry]'))
    CREATE INDEX [IX_FactlessPartyRegisterEntry_Register] ON [gold].[FactlessPartyRegisterEntry] ([Register_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_FactlessPersonAddress_Person' AND object_id = OBJECT_ID(N'[gold].[FactlessPersonAddress]'))
    CREATE INDEX [IX_FactlessPersonAddress_Person] ON [gold].[FactlessPersonAddress] ([Person_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_FactlessPersonAddress_Address' AND object_id = OBJECT_ID(N'[gold].[FactlessPersonAddress]'))
    CREATE INDEX [IX_FactlessPersonAddress_Address] ON [gold].[FactlessPersonAddress] ([Address_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_FactlessPersonPartyRole_Person' AND object_id = OBJECT_ID(N'[gold].[FactlessPersonPartyRole]'))
    CREATE INDEX [IX_FactlessPersonPartyRole_Person] ON [gold].[FactlessPersonPartyRole] ([Person_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_FactlessPersonPartyRole_Party' AND object_id = OBJECT_ID(N'[gold].[FactlessPersonPartyRole]'))
    CREATE INDEX [IX_FactlessPersonPartyRole_Party] ON [gold].[FactlessPersonPartyRole] ([Party_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_FactlessPartyRelationship_Parent' AND object_id = OBJECT_ID(N'[gold].[FactlessPartyRelationship]'))
    CREATE INDEX [IX_FactlessPartyRelationship_Parent] ON [gold].[FactlessPartyRelationship] ([Parent_Party_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_FactlessPartyRelationship_Child' AND object_id = OBJECT_ID(N'[gold].[FactlessPartyRelationship]'))
    CREATE INDEX [IX_FactlessPartyRelationship_Child] ON [gold].[FactlessPartyRelationship] ([Child_Party_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_GoldenPersonLineage_Person' AND object_id = OBJECT_ID(N'[gold].[GoldenPersonLineage]'))
    CREATE INDEX [IX_GoldenPersonLineage_Person] ON [gold].[GoldenPersonLineage] ([DimPerson_ID], [Attribute_Name]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_GoldenPartyLineage_Party' AND object_id = OBJECT_ID(N'[gold].[GoldenPartyLineage]'))
    CREATE INDEX [IX_GoldenPartyLineage_Party] ON [gold].[GoldenPartyLineage] ([DimParty_ID], [Attribute_Name]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_GoldenAddressLineage_Address' AND object_id = OBJECT_ID(N'[gold].[GoldenAddressLineage]'))
    CREATE INDEX [IX_GoldenAddressLineage_Address] ON [gold].[GoldenAddressLineage] ([DimAddress_ID], [Attribute_Name]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_GoldenPartyIdentityLineage_Identity' AND object_id = OBJECT_ID(N'[gold].[GoldenPartyIdentityLineage]'))
    CREATE INDEX [IX_GoldenPartyIdentityLineage_Identity] ON [gold].[GoldenPartyIdentityLineage] ([PartyIdentity_ID], [Attribute_Name]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_PartyAddressLineage_PartyAddress' AND object_id = OBJECT_ID(N'[gold].[PartyAddressLineage]'))
    CREATE INDEX [IX_PartyAddressLineage_PartyAddress] ON [gold].[PartyAddressLineage] ([PartyAddress_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_PersonAddressLineage_PersonAddress' AND object_id = OBJECT_ID(N'[gold].[PersonAddressLineage]'))
    CREATE INDEX [IX_PersonAddressLineage_PersonAddress] ON [gold].[PersonAddressLineage] ([PersonAddress_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_PersonPartyRoleLineage_Role' AND object_id = OBJECT_ID(N'[gold].[PersonPartyRoleLineage]'))
    CREATE INDEX [IX_PersonPartyRoleLineage_Role] ON [gold].[PersonPartyRoleLineage] ([PersonPartyRole_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_PartyRegisterEntryLineage_Entry' AND object_id = OBJECT_ID(N'[gold].[PartyRegisterEntryLineage]'))
    CREATE INDEX [IX_PartyRegisterEntryLineage_Entry] ON [gold].[PartyRegisterEntryLineage] ([PartyRegisterEntry_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_PartyRelationshipLineage_Relationship' AND object_id = OBJECT_ID(N'[gold].[PartyRelationshipLineage]'))
    CREATE INDEX [IX_PartyRelationshipLineage_Relationship] ON [gold].[PartyRelationshipLineage] ([PartyRelationship_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Gold_Lineage_Source_Import' AND object_id = OBJECT_ID(N'[gold].[GoldenPersonLineage]'))
    CREATE INDEX [IX_Gold_Lineage_Source_Import] ON [gold].[GoldenPersonLineage] ([SourceSystem_ID], [ImportBatch_ID], [Recorded_At]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_GoldParty_Lineage_Source_Import' AND object_id = OBJECT_ID(N'[gold].[GoldenPartyLineage]'))
    CREATE INDEX [IX_GoldParty_Lineage_Source_Import] ON [gold].[GoldenPartyLineage] ([SourceSystem_ID], [ImportBatch_ID], [Recorded_At]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_GoldAddress_Lineage_Source_Import' AND object_id = OBJECT_ID(N'[gold].[GoldenAddressLineage]'))
    CREATE INDEX [IX_GoldAddress_Lineage_Source_Import] ON [gold].[GoldenAddressLineage] ([SourceSystem_ID], [ImportBatch_ID], [Recorded_At]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_GoldIdentity_Lineage_Source_Import' AND object_id = OBJECT_ID(N'[gold].[GoldenPartyIdentityLineage]'))
    CREATE INDEX [IX_GoldIdentity_Lineage_Source_Import] ON [gold].[GoldenPartyIdentityLineage] ([SourceSystem_ID], [ImportBatch_ID], [Recorded_At]);
GO

MERGE [gold].[DimAddressType] AS target
USING (VALUES
    (N'REGISTERED'),
    (N'CORRESPONDENCE'),
    (N'RESIDENCE'),
    (N'BUSINESS')
) AS source ([AddressType_Name])
ON target.[AddressType_Name] = source.[AddressType_Name]
WHEN NOT MATCHED THEN
    INSERT ([AddressType_Name]) VALUES (source.[AddressType_Name]);
GO

MERGE [gold].[DimIdentityType] AS target
USING (VALUES
    (N'PESEL'),
    (N'NIP'),
    (N'REGON'),
    (N'KRS'),
    (N'LEI'),
    (N'ID_CARD'),
    (N'PASSPORT'),
    (N'KNF_REGISTER_NUMBER'),
    (N'DECISION_NUMBER')
) AS source ([IdentityType_Name])
ON target.[IdentityType_Name] = source.[IdentityType_Name]
WHEN NOT MATCHED THEN
    INSERT ([IdentityType_Name]) VALUES (source.[IdentityType_Name]);
GO

MERGE [gold].[DimRegisterStatus] AS target
USING (VALUES
    (N'ACTIVE'),
    (N'INACTIVE'),
    (N'SUSPENDED'),
    (N'DEREGISTERED'),
    (N'UNKNOWN')
) AS source ([Status_Name])
ON target.[Status_Name] = source.[Status_Name]
WHEN NOT MATCHED THEN
    INSERT ([Status_Name]) VALUES (source.[Status_Name]);
GO

MERGE [gold].[DimRoleType] AS target
USING (VALUES
    (N'OWNER'),
    (N'BOARD_MEMBER'),
    (N'PROXY'),
    (N'SUPERVISORY_BOARD_MEMBER'),
    (N'LIQUIDATOR'),
    (N'AGENT'),
    (N'EMPLOYEE')
) AS source ([Role_Name])
ON target.[Role_Name] = source.[Role_Name]
WHEN NOT MATCHED THEN
    INSERT ([Role_Name]) VALUES (source.[Role_Name]);
GO

MERGE [gold].[DimPartyRelationshipType] AS target
USING (VALUES
    (N'DIRECT_PARENT'),
    (N'ULTIMATE_PARENT'),
    (N'SHAREHOLDER'),
    (N'RELATED_PARTY')
) AS source ([Relationship_Name])
ON target.[Relationship_Name] = source.[Relationship_Name]
WHEN NOT MATCHED THEN
    INSERT ([Relationship_Name]) VALUES (source.[Relationship_Name]);
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
    (@KRS_SourceSystem_ID, N'PERSON', N'CzlonekZarzadu1_DrugieImie', N'Second_Name'),
    (@KRS_SourceSystem_ID, N'PERSON', N'CzlonekZarzadu1_Nazwisko', N'Last_Name'),
    (@KRS_SourceSystem_ID, N'PERSON', N'CzlonekZarzadu1_PESEL', N'PESEL'),
    (@KRS_SourceSystem_ID, N'PERSON', N'Prokurent1_Imie', N'First_Name'),
    (@KRS_SourceSystem_ID, N'PERSON', N'Prokurent1_DrugieImie', N'Second_Name'),
    (@KRS_SourceSystem_ID, N'PERSON', N'Prokurent1_Nazwisko', N'Last_Name'),
    (@KRS_SourceSystem_ID, N'PERSON', N'Prokurent1_PESEL', N'PESEL'),
    (@KRS_SourceSystem_ID, N'PERSON', N'WspolnikOsoba1_Imie', N'First_Name'),
    (@KRS_SourceSystem_ID, N'PERSON', N'WspolnikOsoba1_DrugieImie', N'Second_Name'),
    (@KRS_SourceSystem_ID, N'PERSON', N'WspolnikOsoba1_Nazwisko', N'Last_Name'),
    (@KRS_SourceSystem_ID, N'PERSON', N'WspolnikOsoba1_PESEL', N'PESEL'),
    (@KRS_SourceSystem_ID, N'PERSON', N'Likwidator1_Imie', N'First_Name'),
    (@KRS_SourceSystem_ID, N'PERSON', N'Likwidator1_DrugieImie', N'Second_Name'),
    (@KRS_SourceSystem_ID, N'PERSON', N'Likwidator1_Nazwisko', N'Last_Name'),
    (@KRS_SourceSystem_ID, N'PERSON', N'Likwidator1_PESEL', N'PESEL'),
    (@KRS_SourceSystem_ID, N'PERSON', N'CzlonekRadyNadzorczej1_Imie', N'First_Name'),
    (@KRS_SourceSystem_ID, N'PERSON', N'CzlonekRadyNadzorczej1_DrugieImie', N'Second_Name'),
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
    (@KNF_AGENT_SourceSystem_ID, N'PERSON', N'DrugieImię', N'Second_Name'),
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
    (@KNF_PRACOWNIK_AGENTA_SourceSystem_ID, N'PERSON', N'DrugieImię', N'Second_Name'),
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
    (@KNF_FIRMY_INWESTYCYJNE_SourceSystem_ID, N'PERSON', N'CzlonekZarzadu1_DrugieImie', N'Second_Name'),
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
