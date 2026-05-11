CREATE TABLE `studies` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int NOT NULL,
	`title` varchar(255) NOT NULL,
	`studyType` enum('retinal_scan','optic_nerve','macular_analysis') NOT NULL,
	`status` enum('draft','analyzing','completed','error') NOT NULL DEFAULT 'draft',
	`analysisResult` text,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `studies_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `studyImages` (
	`id` int AUTO_INCREMENT NOT NULL,
	`studyId` int NOT NULL,
	`fileKey` varchar(512) NOT NULL,
	`url` text NOT NULL,
	`filename` varchar(255) NOT NULL,
	`mimeType` varchar(100) NOT NULL,
	`fileSize` int NOT NULL,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `studyImages_id` PRIMARY KEY(`id`)
);
