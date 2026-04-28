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
            N'RAW_LOAD', N'STAGING_LOAD', N'STANDARDIZATION'
        )),
        CONSTRAINT [CK_ProcessLog_Step_Status] CHECK ([Step_Status] IN (
            N'STARTED', N'SUCCESS', N'FAILED'
        ))
    );
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
        [Sex] NCHAR(1) NULL,
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
        CONSTRAINT [CK_Person_Staging_Sex] CHECK ([Sex] IS NULL OR [Sex] IN (N'K', N'M')),
        CONSTRAINT [CK_Person_Staging_Raw_JSON] CHECK ([Raw_Record_JSON] IS NULL OR ISJSON([Raw_Record_JSON]) = 1)
    );
END;
GO

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
        [Raw_Record_JSON] NVARCHAR(MAX) NULL,
        [Created_At] DATETIME2(0) NOT NULL CONSTRAINT [DF_Party_Staging_Created_At] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [PK_Party_Staging] PRIMARY KEY CLUSTERED ([Staging_ID]),
        CONSTRAINT [FK_Party_Staging_ImportBatch] FOREIGN KEY ([ImportBatch_ID])
            REFERENCES [meta].[ImportBatch] ([ImportBatch_ID]),
        CONSTRAINT [FK_Party_Staging_RawFile] FOREIGN KEY ([RawFile_ID])
            REFERENCES [raw].[RawFile] ([RawFile_ID]),
        CONSTRAINT [CK_Party_Staging_Identifiers_JSON] CHECK ([Identifiers_JSON] IS NULL OR ISJSON([Identifiers_JSON]) = 1),
        CONSTRAINT [CK_Party_Staging_Raw_JSON] CHECK ([Raw_Record_JSON] IS NULL OR ISJSON([Raw_Record_JSON]) = 1)
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
    (N'GLEIF_L1', N'GLEIF Level 1', 75),
    (N'GLEIF_L2', N'GLEIF Level 2', 75)
) AS source ([SourceSystem_Code], [SourceSystem_Name], [Trust_Level])
ON target.[SourceSystem_Code] = source.[SourceSystem_Code]
WHEN NOT MATCHED THEN
    INSERT ([SourceSystem_Code], [SourceSystem_Name], [Trust_Level])
    VALUES (source.[SourceSystem_Code], source.[SourceSystem_Name], source.[Trust_Level]);
GO

DECLARE @DefaultSourceSystem_ID INT = (
    SELECT [SourceSystem_ID]
    FROM [meta].[SourceSystem]
    WHERE [SourceSystem_Code] = N'CEIDG'
);

MERGE [meta].[ColumnMapping] AS target
USING (VALUES
    (@DefaultSourceSystem_ID, N'PARTY', N'name', N'Name'),
    (@DefaultSourceSystem_ID, N'PARTY', N'nazwa', N'Name'),
    (@DefaultSourceSystem_ID, N'PARTY', N'nazwa_firmy', N'Name'),
    (@DefaultSourceSystem_ID, N'PERSON', N'firstName', N'First_Name'),
    (@DefaultSourceSystem_ID, N'PERSON', N'imie', N'First_Name'),
    (@DefaultSourceSystem_ID, N'PERSON', N'surname', N'Last_Name'),
    (@DefaultSourceSystem_ID, N'PERSON', N'nazwisko', N'Last_Name'),
    (@DefaultSourceSystem_ID, N'PERSON', N'pesel', N'PESEL'),
    (@DefaultSourceSystem_ID, N'PARTY', N'nip', N'Identifiers_JSON'),
    (@DefaultSourceSystem_ID, N'PARTY', N'regon', N'Identifiers_JSON'),
    (@DefaultSourceSystem_ID, N'PARTY', N'krs', N'Identifiers_JSON')
) AS source ([SourceSystem_ID], [Entity_Type], [Source_Column_Name], [Canonical_Column_Name])
ON target.[SourceSystem_ID] = source.[SourceSystem_ID]
    AND target.[Entity_Type] = source.[Entity_Type]
    AND target.[Source_Column_Name] = source.[Source_Column_Name]
WHEN NOT MATCHED THEN
    INSERT ([SourceSystem_ID], [Entity_Type], [Source_Column_Name], [Canonical_Column_Name])
    VALUES (source.[SourceSystem_ID], source.[Entity_Type], source.[Source_Column_Name], source.[Canonical_Column_Name]);
GO
