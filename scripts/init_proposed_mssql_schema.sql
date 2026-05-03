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

DECLARE @CEIDG_SourceSystem_ID INT = (
    SELECT [SourceSystem_ID]
    FROM [meta].[SourceSystem]
    WHERE [SourceSystem_Code] = N'CEIDG'
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

DECLARE @GLEIF_L1_SourceSystem_ID INT = (
    SELECT [SourceSystem_ID]
    FROM [meta].[SourceSystem]
    WHERE [SourceSystem_Code] = N'GLEIF_L1'
);

MERGE [meta].[ColumnMapping] AS target
USING (VALUES
    -- PARTY (GLEIF L1)
    (@GLEIF_L1_SourceSystem_ID, N'PARTY', N'Entity.LegalName', N'Name'),
    (@GLEIF_L1_SourceSystem_ID, N'PARTY', N'Entity.LegalJurisdiction', N'Registration_Country'),
    (@GLEIF_L1_SourceSystem_ID, N'PARTY', N'Entity.LegalForm.EntityLegalFormCode', N'Legal_Entity_Type'),
    (@GLEIF_L1_SourceSystem_ID, N'PARTY', N'Registration.InitialRegistrationDate', N'Establishment_Date'),

    -- adres legalny (Street/City/Postal/Country) bez parsera
    (@GLEIF_L1_SourceSystem_ID, N'PARTY', N'Entity.LegalAddress.FirstAddressLine', N'Street'),
    (@GLEIF_L1_SourceSystem_ID, N'PARTY', N'Entity.LegalAddress.City', N'City'),
    (@GLEIF_L1_SourceSystem_ID, N'PARTY', N'Entity.LegalAddress.PostalCode', N'Postal_Code'),
    (@GLEIF_L1_SourceSystem_ID, N'PARTY', N'Entity.LegalAddress.Country', N'Country'),

    -- identyfikator: LEI do Identifiers_JSON
    (@GLEIF_L1_SourceSystem_ID, N'PARTY', N'LEI', N'Identifiers_JSON')
) AS source ([SourceSystem_ID], [Entity_Type], [Source_Column_Name], [Canonical_Column_Name])
ON target.[SourceSystem_ID] = source.[SourceSystem_ID]
AND target.[Entity_Type] = source.[Entity_Type]
AND target.[Source_Column_Name] = source.[Source_Column_Name]
WHEN NOT MATCHED THEN
    INSERT ([SourceSystem_ID], [Entity_Type], [Source_Column_Name], [Canonical_Column_Name])
    VALUES (source.[SourceSystem_ID], source.[Entity_Type], source.[Source_Column_Name], source.[Canonical_Column_Name]);
GO

DECLARE @GLEIF_L2_SourceSystem_ID INT = (
    SELECT [SourceSystem_ID]
    FROM [meta].[SourceSystem]
    WHERE [SourceSystem_Code] = N'GLEIF_L2'
);

MERGE [meta].[ColumnMapping] AS target
USING (VALUES
    -- PARTY (GLEIF L2)
    (@GLEIF_L2_SourceSystem_ID, N'PARTY', N'StartNode.NodeID', N'Identifiers_JSON'),
    (@GLEIF_L2_SourceSystem_ID, N'PARTY', N'EndNode.NodeID', N'Identifiers_JSON')
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

MERGE [meta].[ColumnMapping] AS target
USING (VALUES
    -- PARTY (KRS) - data/csv/krs.csv
    (@KRS_SourceSystem_ID, N'PARTY', N'nazwa', N'Name'),
    (@KRS_SourceSystem_ID, N'PARTY', N'nazwaSkrocona', N'Short_Name'),
    (@KRS_SourceSystem_ID, N'PARTY', N'formaPrawna', N'Legal_Entity_Type'),
    (@KRS_SourceSystem_ID, N'PARTY', N'dataRejestracji', N'Establishment_Date'),
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

    -- PARTY (KNF_AGENT)
    (@KNF_AGENT_SourceSystem_ID, N'PARTY', N'Firma/Nazwa', N'Name'),
    (@KNF_AGENT_SourceSystem_ID, N'PARTY', N'Miejscowość', N'City'),
    (@KNF_AGENT_SourceSystem_ID, N'PARTY', N'Ulica i numer', N'Street'),
    (@KNF_AGENT_SourceSystem_ID, N'PARTY', N'Kod pocztowy', N'Postal_Code'),
    (@KNF_AGENT_SourceSystem_ID, N'PARTY', N'Numer NIP', N'Identifiers_JSON'),
    (@KNF_AGENT_SourceSystem_ID, N'PARTY', N'Numer KRS', N'Identifiers_JSON')
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

MERGE [meta].[ColumnMapping] AS target
USING (VALUES
    -- PERSON (KNF_PRACOWNIK_AGENTA) - data/csv/KNF_Rejestr_posrednikow_ubezpieczeniowych_pracownik_agenta.csv
    (@KNF_PRACOWNIK_AGENTA_SourceSystem_ID, N'PERSON', N'Imię agenta', N'First_Name'),
    (@KNF_PRACOWNIK_AGENTA_SourceSystem_ID, N'PERSON', N'Nazwisko agenta', N'Last_Name'),

    -- PARTY (KNF_PRACOWNIK_AGENTA) - agent jako podmiot
    (@KNF_PRACOWNIK_AGENTA_SourceSystem_ID, N'PARTY', N'Nazwa agenta', N'Name'),
    (@KNF_PRACOWNIK_AGENTA_SourceSystem_ID, N'PARTY', N'Numer NIP agenta', N'Identifiers_JSON'),
    (@KNF_PRACOWNIK_AGENTA_SourceSystem_ID, N'PARTY', N'Numer KRS agenta', N'Identifiers_JSON')
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
    (@KNF_FIRMY_INWESTYCYJNE_SourceSystem_ID, N'PARTY', N'Adres siedziby', N'Street')
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
    (@KNF_PIENIADZ_ELEKTRONICZNY_SourceSystem_ID, N'PARTY', N'KRS', N'Identifiers_JSON')
) AS source ([SourceSystem_ID], [Entity_Type], [Source_Column_Name], [Canonical_Column_Name])
ON target.[SourceSystem_ID] = source.[SourceSystem_ID]
AND target.[Entity_Type] = source.[Entity_Type]
AND target.[Source_Column_Name] = source.[Source_Column_Name]
WHEN NOT MATCHED THEN
    INSERT ([SourceSystem_ID], [Entity_Type], [Source_Column_Name], [Canonical_Column_Name])
    VALUES (source.[SourceSystem_ID], source.[Entity_Type], source.[Source_Column_Name], source.[Canonical_Column_Name]);
GO
